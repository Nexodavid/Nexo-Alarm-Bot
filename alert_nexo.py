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
from datetime import datetime, timedelta

PRICE_THRESHOLD = 1.00
NEWS_FEED = "https://news.google.com/rss/search?q=Nexo+crypto&hl=en-US&gl=US&ceid=US:en"
TWITTER_URL = "https://nitter.net/search?f=tweets&q=Nexo+crypto"
PRICE_API = "https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd"

EMAIL_FROM = os.environ['EMAIL_USER']
EMAIL_PASS = os.environ['EMAIL_PASS']
EMAIL_TO = os.environ['EMAIL_USER']
EMAIL_SUBJECT = "[Nexo Alert] Updates from News, Tweets & Price"
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

def fetch_news():
    feed = feedparser.parse(NEWS_FEED)
    previous = set(open("news_cache.txt", encoding="utf-8").read().splitlines()) if os.path.exists("news_cache.txt") else set()
    new_items = []
    with open("news_cache.txt", "a", encoding="utf-8") as f:
        for entry in feed.entries[:10]:
            key = entry.link.strip()
            if key not in previous:
                line = f"<b>📰 <a href='{entry.link}'>{entry.title}</a></b>"
                new_items.append(line)
                f.write(f"{key}\n")
    return new_items

def fetch_tweets():
    try:
        resp = requests.get(TWITTER_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        tweets = soup.find_all('div', class_='tweet-body')[:3]
        previous = set(open("tweet_cache.txt", encoding="utf-8").read().splitlines()) if os.path.exists("tweet_cache.txt") else set()
        tweet_items = []
        with open("tweet_cache.txt", "a", encoding="utf-8") as f:
            for div in tweets:
                text = div.get_text(strip=True)
                if text not in previous:
                    tweet_items.append(f"<b>🐦 Tweet:</b> {text}")
                    f.write(f"{text}\n")
        return tweet_items
    except Exception:
        return ["<b>⚠️ 트위터 수집 실패</b>"]

def fetch_price():
    try:
        price = requests.get(PRICE_API).json()['nexo']['usd']
    except:
        price = 0

    with open("price_cache.txt", "a") as f:
        f.write(f"{price}\n")

    with open("price_cache.txt") as f:
        prices = [float(x.strip()) for x in f if x.strip()]
    if len(prices) > 28:
        prices = prices[-28:]

    dates = [datetime.now() - timedelta(hours=6 * i) for i in range(len(prices) - 1, -1, -1)]

    plt.style.use("default")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(dates, prices, marker='o', linewidth=2, color='#0077CC')
    ax.axhline(PRICE_THRESHOLD, color='red', linestyle='dashed', linewidth=1)
    ax.set_title("NEXO Price - Last 7 Days", fontsize=13)
    ax.set_ylabel("Price (USD)")
    ax.set_xlabel("Date")
    ax.tick_params(axis='x', rotation=30)
    fig.tight_layout()
    plt.savefig("chart.png")
    plt.close()

    previous_price = prices[-2] if len(prices) > 1 else price
    delta = price - previous_price
    percent = (delta / previous_price * 100) if previous_price else 0
    direction = "📈 Increase" if delta > 0 else "📉 Decrease" if delta < 0 else "➖ No Change"
    change_text = f"<b>{direction} ({percent:+.2f}%)</b>"
    price_text = f"<b>📊 NEXO Current Price: ${price:.2f}</b>"

    return price, f"{price_text}\n{change_text}"

def send_email(body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = EMAIL_SUBJECT
    msg.attach(MIMEText(body.replace('<br>', '\n'), 'plain'))

    with open("chart.png", "rb") as img:
        chart_img = MIMEImage(img.read())
        chart_img.add_header('Content-Disposition', 'attachment', filename='chart.png')
        msg.attach(chart_img)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print("✅ 이메일 전송 완료")

def send_telegram(caption):
    try:
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

# 실행
news = fetch_news()
tweets = fetch_tweets()
price, delta = fetch_price()

if not news and not tweets:
    combined = "<b>🔇 새로운 뉴스나 트윗 없음</b><br>" + delta
else:
    combined = f"{delta}<br><br>" + "<br>".join(news + tweets)

send_email(combined)
send_telegram(combined)
