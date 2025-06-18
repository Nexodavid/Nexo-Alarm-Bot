import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
from bs4 import BeautifulSoup

# 설정값
RSS_URL = "https://news.google.com/rss/search?q=Nexo+crypto&hl=en-US&gl=US&ceid=US:en"
TWITTER_SEARCH_URL = "https://nitter.net/search?f=tweets&q=Nexo+crypto&since=&until=&near="
PRICE_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd"
EMAIL_FROM = os.environ['EMAIL_USER']
EMAIL_TO = "davidohthai@gmail.com"
EMAIL_SUBJECT = "[Nexo Alert] 새로운 뉴스/트윗/가격변동"

# Google 뉴스 파싱
news_feed = feedparser.parse(RSS_URL)
news_items = []
for entry in news_feed.entries[:5]:
    title = entry.title
    link = entry.link
    published = entry.get("published", "")
    news_items.append(f"[뉴스] {title} ({published})\n{link}\n")

# 트위터 검색 (Nitter 사용)
twitter_items = []
try:
    resp = requests.get(TWITTER_SEARCH_URL, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    tweets = soup.find_all('div', class_='tweet-body')[:3]
    for tweet in tweets:
        text = tweet.get_text(strip=True)
        twitter_items.append(f"[트윗] {text}\n")
except Exception as e:
    twitter_items.append(f"[트윗] 트위터 정보 수집 실패: {e}\n")

# 가격 확인
price_info = requests.get(PRICE_API_URL).json()
nexo_price = price_info.get("nexo", {}).get("usd", 0)
price_message = f"[가격] 현재 NEXO 가격: ${nexo_price:.4f}"

# 이메일 전송
all_items = news_items + twitter_items + [price_message]
if all_items:
    body = "\n".join(all_items)
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = EMAIL_SUBJECT
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, os.environ['EMAIL_PASS'])
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            print("이메일 전송 완료")
    except Exception as e:
        print(f"이메일 전송 실패: {e}")
else:
    print("새로운 정보 없음")

# 텔레그램 전송
telegram_token = os.environ['TELEGRAM_TOKEN']
telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']
telegram_msg = "\n".join(all_items)
telegram_api = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
telegram_data = {"chat_id": telegram_chat_id, "text": telegram_msg}
try:
    requests.post(telegram_api, data=telegram_data)
    print("텔레그램 전송 완료")
except Exception as e:
    print(f"텔레그램 전송 실패: {e}")
