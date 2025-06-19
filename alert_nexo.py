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

PRICE_THRESHOLD = 1.00
NEWS_FEED = "https://news.google.com/rss/search?q=Nexo+crypto&hl=en-US&gl=US&ceid=US:en"
TWITTER_URL = "https://nitter.net/search?f=tweets&q=Nexo+crypto&since=&until=&near="
PRICE_API = "https://api.coingecko.com/api/v3/simple/price?ids=nexo&vs_currencies=usd"

EMAIL_FROM = os.environ['EMAIL_USER']
EMAIL_PASS = os.environ['EMAIL_PASS']
EMAIL_TO = os.environ['EMAIL_USER']
EMAIL_SUBJECT = "[Nexo Alert] New News/Tweets/Price Changes"
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# Fetch and deduplicate news
def fetch_news():
    feed = feedparser.parse(NEWS_FEED)
    previous = set(open("news_cache.txt", encoding="utf-8").read().splitlines()) if os.path.exists("news_cache.txt") else set()
    new_items = []
    with open("news_cache.txt", "a", encoding="utf-8") as f:
        for entry in feed.entries[:10]:
            key = entry.link.strip()
            if key not in previous:
                line = f"[News] {entry.title} ({entry.link})"
                new_items.append(line)
                f.write(f"{key}\n")
    return new_items

# Fetch and deduplicate tweets
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
                    tweet_items.append(f"[Tweet] {text}")
                    f.write(f"{text}\n")
        return tweet_items
    except Exception:
        return ["[Tweet] Failed to retrieve tweets"]

# Fetch price and draw chart
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

    # Draw chart
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(prices, marker='o', linewidth=2, label="NEXO")
    ax.axhline(PRICE_THRESHOLD, color='red', linestyle='dashed', linewidth=1)
    ax.set_title("NEXO Price Trend", fontsize=12)
    ax.set_ylabel("Price (USD)")
    ax.set_xlabel("Time")
    ax.legend()
    fig.tight_layout()
    plt.savefig("chart.png")
    plt.close()

    prev_price = prices[-2] if len(prices) > 1 else price
    delta = price - prev_price
    percent = (delta / prev_price * 100) if prev_price else 0
    direction = "📈 Up" if delta > 0 else "📉 Down" if delta < 0 else "➖ No change"
    delta_msg = f"{direction} ({percent:+.2f}%)"

    return price, delta_msg

# Email
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
    print("✅ Email sent")

# Telegram
def send_telegram(caption):
    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open("chart.png", "rb") as img:
            response = requests.post(telegram_url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption[:1024]
            }, files={"photo": img})
        print(response.text)
        print("✅ Telegram sent")
    except Exception as e:
        print(f"⚠️ Telegram failed: {e}")

# Execute
news = fetch_news()
tweets = fetch_tweets()
price, delta = fetch_price()

price_info = f"\n\n📊 Current NEXO Price: ${price:.2f}\n{delta}"
if not news and not tweets:
    message = "No new news or tweets." + price_info
else:
    message = "\n".join(news + tweets) + price_info

send_email(message)
send_telegram(message)
