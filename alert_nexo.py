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
import matplotlib.dates as mdates
from html import escape
from datetime import datetime

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

def truncate_html(text, max_len=1024):
    result = []
    total = 0
    for line in text.splitlines():
        if total + len(line) + 1 > max_len:
            break
        result.append(line)
        total += len(line) + 1
    return "\n".join(result)

def limit_file_lines(filename, max_lines=100):
    with open(filename, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) > max_lines:
            f.seek(0)
            f.writelines(lines[-max_lines:])
            f.truncate()

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
    limit_file_lines("news_cache.txt", 100)
    return items

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
        limit_file_lines("tweet_cache.txt", 100)
        return items
    except:
        return ["⚠️ Failed to fetch Twitter data"]

def fetch_price():
    try:
        price = requests.get(PRICE_API).json()['nexo']['usd']
    except:
        price = 0

    today = datetime.today().strftime("%Y-%m-%d")

    # 기존 데이터 읽기
    lines = []
    if os.path.exists("price_cache.txt"):
        with open("price_cache.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

    # 중복된 오늘 날짜 제거
    lines = [line for line in lines if not line.startswith(today)]
    lines.append(f"{today},{price}")

    # 최근 60개까지만 유지
    if len(lines) > 60:
        lines = lines[-60:]

    # 저장
    with open("price_cache.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 날짜와 가격 분리
    dates, prices = [], []
    for line in lines:
        if ',' in line:
            d, p = line.split(',')
            dates.append(datetime.strptime(d, "%Y-%m-%d").date())  # ✅ 날짜 변환
            prices.append(float(p))

    # ✅ 차트 그리기
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(dates, prices, marker='o', linewidth=2, label="NEXO", color="#007ACC")
    ax.axhline(PRICE_THRESHOLD, color='red', linestyle='dashed', linewidth=1)
    ax.set_facecolor("#f9f9f9")
    fig.patch.set_facecolor("#ffffff")
    ax.set_title("NEXO Price Trend (7 days)", fontsize=12)
    ax.set_ylabel("Price (USD)")
    ax.set_xlabel("Date")
    ax.grid(True)

    # ✅ x축 날짜 포맷 지정 (일 단위만 보이게)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

    # ✅ 날짜 라벨 자동 회전
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.savefig("chart.png")
    plt.close()

    # ✅ 가격 변화율
    prev = prices[-2] if len(prices) > 1 else price
    delta = price - prev
    percent = (delta / prev * 100) if prev != 0 else 0
    change = f"{'📈 Increase' if delta > 0 else '📉 Decrease' if delta < 0 else '➖ No Change'} ({percent:+.2f}%)"
    return price, change
    
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
