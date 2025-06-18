import feedparser
import requests
import smtplib
import os
import matplotlib.pyplot as plt
from email.message import EmailMessage
from datetime import datetime

# 환경변수 불러오기
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRICE_THRESHOLD = 1.00

# 이전 뉴스 캐시 불러오기
try:
    with open("news_cache.txt", "r", encoding="utf-8") as f:
        cached_titles = set(line.strip() for line in f.readlines())
except FileNotFoundError:
    cached_titles = set()

# 뉴스 수집
feed = feedparser.parse("https://cointelegraph.com/rss")
new_entries = []
for entry in feed.entries[:10]:
    title = entry.title.strip()
    if "nexo" in title.lower() and title not in cached_titles:
        new_entries.append(f"- {title}")
        cached_titles.add(title)

# 캐시 저장
with open("news_cache.txt", "w", encoding="utf-8") as f:
    for title in cached_titles:
        f.write(title + "\n")

# 내용 생성
if new_entries:
    news_body = "\n".join(new_entries)
else:
    news_body = "새로운 소식은 없습니다."

# 트위터 검색 (단순 웹 스크래핑 방식)
tweet_body = ""
try:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get("https://nitter.net/search?f=tweets&q=nexo&since=&until=", headers=headers)
    if "nexo" in r.text.lower():
        tweet_body = "최근 트윗에서 'nexo' 언급이 확인되었습니다."
    else:
        tweet_body = "관련 트윗이 없습니다."
except Exception as e:
    tweet_body = f"트위터 확인 실패: {e}"

# 가격 조회 및 변동률 계산
price_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd")
nexo_price = price_res.json().get("nexo", {}).get("usd", 0)

try:
    with open("previous_price.txt", "r") as f:
        prev_price = float(f.read().strip())
except:
    prev_price = nexo_price

change_percent = ((nexo_price - prev_price) / prev_price) * 100 if prev_price else 0

with open("previous_price.txt", "w") as f:
    f.write(str(nexo_price))

# 차트 생성
prices = [1.20, 1.18, 1.22, 1.19, nexo_price]  # 예시 데이터
plt.figure()
plt.plot(prices, marker='o')
plt.title("NEXO 가격 추이")
plt.xlabel("시간")
plt.ylabel("가격 (USD)")
plt.grid(True)
plt.axhline(y=PRICE_THRESHOLD, color='r', linestyle='--')
plt.savefig("chart.png")

# 이메일 전송
msg = EmailMessage()
msg["Subject"] = f"[NEXO 알림] 현재 가격 ${nexo_price:.2f} ({change_percent:+.2f}%)"
msg["From"] = EMAIL_USER
msg["To"] = EMAIL_USER
body = f"[NEXO 가격] ${nexo_price:.2f} ({change_percent:+.2f}%)\n\n[뉴스]\n{news_body}\n\n[트위터]\n{tweet_body}"
msg.set_content(body)
with open("chart.png", "rb") as img:
    msg.add_attachment(img.read(), maintype="image", subtype="png", filename="chart.png")

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

# 텔레그램 전송
try:
    if nexo_price < PRICE_THRESHOLD:
        caption = f"⚠️ NEXO 가격이 ${PRICE_THRESHOLD} 아래입니다!"
    elif abs(change_percent) >= 5:
        caption = f"📈 가격 변동률 {change_percent:+.2f}% 감지됨! 현재 ${nexo_price:.2f}"
    else:
        caption = f"NEXO 현재 가격은 ${nexo_price:.2f}"

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open("chart.png", "rb") as img:
        response = requests.post(telegram_url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption
        }, files={"photo": img})
    print(response.text)
except Exception as e:
    print(f"❌ 텔레그램 실패: {e}")
