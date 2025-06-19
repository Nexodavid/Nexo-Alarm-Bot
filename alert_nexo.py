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

# 설정
PRICE_THRESHOLD = 1.00
NEWS_FEED = "https://news.google.com/rss/search?q=Nexo+crypto&hl=en-US&gl=US&ceid=US:en"
TWITTER_URL = "https://nitter.net/search?f=tweets&q=Nexo+crypto"
PRICE_API = "https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd"

EMAIL_FROM = os.environ['EMAIL_USER']
EMAIL_PASS = os.environ['EMAIL_PASS']
EMAIL_TO = os.environ['EMAIL_USER']
EMAIL_SUBJECT = "[Nexo Alert] Update: News, Twitter, Price"
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# HTML 메시지 트렁크
def truncate_html(text, max_len=1024):
    result = []
    total = 0
    for line in text.splitlines():
        if total + len(line) + 1 > max_len:
            break
        result.append(line)
        total += len(line) + 1
    return "\n".join(result)

# 뉴스 수집
def fetch_news():
    feed = feedparser.parse(NEWS_FEED)
    previous = set(open("news_cache.txt", encoding="utf-8").read().splitlines())
    items = []
    with open("news_cache.txt", "a", encoding="utf-8") as f:
        for entry in feed.entries[:10]:
            key = entry.link.strip()
            if key not in previous:
                text = f"📰 <b>{escape(entry.title)}</b>\n<a href='{entry.link}'>🔗 Read more</a>"
                items.append(text)
                f.write(f"{key}\n")
    return items

# 트윗 수집
def fetch_tweets():
    try:
        resp = requests.get(TWITTER_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        divs = soup.find_all('div', class_='tweet-body')[:3]
        previous = set(open("tweet_cache.txt", encoding="utf-8").read().splitlines())
        items = []
        with open("tweet_cache.txt", "a", encoding="utf-8") as f:
            for div in divs:
                text = div.get_text(strip=True)
                if text not in previous:
                    items.append(f"🐦 <i>{escape(text)}</i>")
                    f.write(f"{text}\n")
        return items
    except:
        return ["⚠️ Failed to fetch Twitter data"]

# 가격 수집 및 그래프 생성
def fetch_price():
    try:
        price = requests.get(PRICE_API).json()['nexo']['usd']
    except:
        price = 0
    with open("price_cache.txt", "a") as f:
        f.write(f"{price}\n")
    with open("price_cache.txt") as f:
        prices = [float(x.strip()) for x in f.readlines() if x.strip()]
    if len(prices) > 20:
        prices = prices[-20:]

    # 차트 생성
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(prices, marker='o', linewidth=2, label="NEXO", color="#007ACC")
    ax.axhline(PRICE_THRESHOLD, color='red', linestyle='dashed', linewidth=1)
    ax.set_title("NEXO Price Trend")
    ax.set_ylabel("Price (USD)")
    ax.set_xlabel("Time")
    ax.grid(True)
    fig.tight_layout()
    plt.savefig("chart.png")
    plt.close()

    # 가격 변화율 계산
    previous = prices[-2] if len(prices) > 1 else price
    delta = price - previous
    percent = (delta / previous * 100) if previous != 0 else 0
    change = f"{'📈 Increase' if delta > 0 else '📉 Decrease' if delta < 0 else '➖ No Change'} ({percent:+.2f}%)"
    return price, change

# 이메일 전송
def send_email(body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = EMAIL_SUBJECT
    msg.attach(MIMEText(body, 'plain'))

    with open("chart.png", "rb") as img:
        chart = MIMEImage(img.read())
        chart.add_header('Content-Disposition', 'attachment', filename='chart.png')
        msg.attach(chart)

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print("✅ 이메일 전송 완료")

# 텔레그램 전송
def send_telegram(body):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open("chart.png", "rb") as img:
            caption = truncate_html(body, 1024)
            res = requests.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
                "parse_mode": "HTML"
            }, files={"photo": img})
        print("✅ 텔레그램 전송 완료")
    except Exception as e:
        print(f"⚠️ 텔레그램 전송 실패: {e}")

# 실행
news_items = fetch_news()
tweet_items = fetch_tweets()
price, movement = fetch_price()

summary = f"<b>📊 NEXO Current Price: ${price:.2f}</b>\n{movement}\n\n"

if not news_items and not tweet_items:
    alert_text = summary + "🔕 No new news or tweets."
else:
    alert_text = summary + "\n".join(news_items + tweet_items)

send_email(alert_text.replace("<", "").replace(">", ""))  # 이메일은 HTML 제거
send_telegram(alert_text)
