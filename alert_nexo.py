import requests
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import os
from datetime import datetime

# 설정값
EMAIL_FROM = os.environ['EMAIL_USER']
EMAIL_PASS = os.environ['EMAIL_PASS']
EMAIL_TO = "davidohthai@gmail.com"
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
EMAIL_SUBJECT = "[Nexo Alert] 새로운 뉴스/트윗/가격변동"
PRICE_THRESHOLD = 1.0

# 가격 차트 가져오기 (최근 7일)
price_chart_url = "https://api.coingecko.com/api/v3/coins/nexo/market_chart?vs_currency=usd&days=7"
price_data = requests.get(price_chart_url).json()
timestamps = [datetime.fromtimestamp(p[0] / 1000) for p in price_data['prices']]
prices = [p[1] for p in price_data['prices']]

# 가격 차트 이미지 생성
plt.figure(figsize=(8, 4))
plt.plot(timestamps, prices, label="NEXO Price (USD)")
plt.title("NEXO Price - Last 7 Days")
plt.xlabel("Date")
plt.ylabel("USD")
plt.grid(True)
plt.tight_layout()
plt.savefig("chart.png")

# Coingecko 현재 가격
price_api_url = "https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd"
nexo_price = requests.get(price_api_url).json()["nexo"]["usd"]
price_message = f"현재 NEXO 가격: ${nexo_price:.4f}"

# RSS 뉴스 가져오기
rss_url = "https://news.google.com/rss/search?q=Nexo+crypto&hl=en-US&gl=US&ceid=US:en"
news_feed = feedparser.parse(rss_url)
news_items = [f"[뉴스] {entry.title} ({entry.link})" for entry in news_feed.entries[:5]]

# 트위터 감지 (nitter)
twitter_url = "https://nitter.net/search?f=tweets&q=Nexo+crypto&since=&until=&near="
twitter_items = []
try:
    resp = requests.get(twitter_url, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    tweets = soup.find_all('div', class_='tweet-body')[:3]
    for tweet in tweets:
        text = tweet.get_text(strip=True)
        twitter_items.append(f"[트윗] {text}")
except Exception as e:
    twitter_items.append("[트윗] 트위터 수집 실패")

# 모든 정보 합치기
all_items = news_items + twitter_items + [price_message]
body = "\n".join(all_items)

# 이메일 전송
try:
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = EMAIL_SUBJECT
    msg.attach(MIMEText(body, 'plain'))
    with open("chart.png", "rb") as img:
        chart_img = MIMEImage(img.read())
        chart_img.add_header('Content-Disposition', 'attachment; filename="chart.png"')
        msg.attach(chart_img)
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print("이메일 전송 완료")
except Exception as e:
    print(f"이메일 실패: {e}")

# 텔레그램 전송 (차트 포함)
try:
    caption = body + (f"\n⚠️ NEXO 가격이 $1.00 아래입니다!" if nexo_price < PRICE_THRESHOLD else "")
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open("chart.png", "rb") as img:
        requests.post(telegram_url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption
        }, files={"photo": img})
    print("텔레그램 전송 완료")
except Exception as e:
    print(f"텔레그램 실패: {e}")
