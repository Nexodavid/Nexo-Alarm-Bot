# alert_nexo.py

import os
import requests
import feedparser
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import smtplib
import matplotlib.pyplot as plt
from datetime import datetime
from html import escape

# === 설정 ===
PRICE_THRESHOLD = 1.00
NEWS_FEED = "https://news.google.com/rss/search?q=Nexo+crypto&hl=en-US&gl=US&ceid=US:en"
TWITTER_URL = "https://nitter.net/search?f=tweets&q=Nexo+crypto"
PRICE_API = "https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd"

EMAIL_FROM = os.environ['EMAIL_USER']
EMAIL_PASS = os.environ['EMAIL_PASS']
EMAIL_TO = os.environ['EMAIL_USER']
EMAIL_SUBJECT = "[Nexo Alert] 새로운 뉴스/트윗/가격변동"
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# === 뉴스 수집 ===
def fetch_news():
    feed = feedparser.parse(NEWS_FEED)
    previous = set(open("news_cache.txt", encoding="utf-8").read().splitlines())
    new_items = []
    with open("news_cache.txt", "a", encoding="utf-8") as f:
        for entry in feed.entries[:10]:
            link = entry.link.strip()
            if link not in previous:
                title = entry.title
                new_items.append((title, link))
                f.write(link + "\n")
    return new_items

# === 트윗 수집 ===
def fetch_tweets():
    try:
        resp = requests.get(TWITTER_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        tweets = soup.find_all('div', class_='tweet-body')[:3]
        previous = set(open("tweet_cache.txt", encoding="utf-8").read().splitlines())
        tweet_items = []
        with open("tweet_cache.txt", "a", encoding="utf-8") as f:
            for div in tweets:
                text = div.get_text(strip=True)
                if text and text not in previous:
                    tweet_items.append(text)
                    f.write(text + "\n")
        return tweet_items
    except Exception:
        return ["[Twitter] 트윗 수집 실패"]

# === 가격 수집 및 차트 생성 ===
def fetch_price():
    try:
        price = requests.get(PRICE_API).json()['nexo']['usd']
    except:
        price = 0.0

    with open("price_cache.txt", "a") as f:
        f.write(f"{price}\n")

    with open("price_cache.txt") as f:
        prices = [float(x.strip()) for x in f.readlines() if x.strip()]
    if len(prices) > 50:
        prices = prices[-50:]

    plt.style.use('seaborn-v0_8-deep')
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(prices, marker='o', linewidth=2, label="NEXO")
    ax.axhline(PRICE_THRESHOLD, color='red', linestyle='dashed', linewidth=1)
    ax.set_title("NEXO Price - Last 7 Days", fontsize=12)
    ax.set_ylabel("Price (USD)")
    ax.set_xlabel("Date")
    ax.legend()
    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close()

    previous_price = prices[-2] if len(prices) > 1 else price
    delta = price - previous_price
    percent = (delta / previous_price * 100) if previous_price != 0 else 0
    direction = "📈 Increase" if delta > 0 else "📉 Decrease" if delta < 0 else "➖ No Change"
    change_text = f"{direction} ({percent:+.2f}%)"
    return price, change_text

# === 이메일 전송 ===
def send_email(body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = EMAIL_SUBJECT
    msg.attach(MIMEText(body, 'plain'))

    with open("chart.png", "rb") as img:
        chart_img = MIMEImage(img.read())
        chart_img.add_header('Content-Disposition', 'attachment', filename='chart.png')
        msg.attach(chart_img)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print("✅ 이메일 전송 완료")

# === 텔레그램 전송 ===
def send_telegram(price, delta, news, tweets):
    try:
        caption = f"📊 <b>NEXO Current Price:</b> ${price:.2f}\n{escape(delta)}"

        for title, url in news:
            safe_title = escape(title)
            caption += f'\n📰 <b><a href="{url}">{safe_title}</a></b>'

        for t in tweets:
            safe_tweet = escape(t)
            caption += f"\n💬 {safe_tweet}"

        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open("chart.png", "rb") as img:
            response = requests.post(telegram_url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption[:1024],
                "parse_mode": "HTML"
            }, files={"photo": img})
        print(response.text)
        print("✅ 텔레그램 전송 완료")
    except Exception as e:
        print(f"⚠️ 텔레그램 실패: {e}")

# === 실행 ===
news = fetch_news()
tweets = fetch_tweets()
price, delta = fetch_price()

if not news and not tweets:
    combined = f"No new updates in news or Twitter.\n\nNEXO current price: ${price:.2f}\n{delta}"
else:
    combined = f"NEXO current price: ${price:.2f}\n{delta}\n\n"
    combined += "\n".join([f"[뉴스] {t} ({u})" for t, u in news])
    combined += "\n" + "\n".join([f"[트윗] {t}" for t in tweets])

send_email(combined)
send_telegram(price, delta, news, tweets)
