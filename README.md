# 📈 Nexo Alarm Bot

자동화된 Nexo 알림 봇입니다.  
이 봇은 **Nexo 관련 뉴스**, **트위터 게시물**, **가격 변동**을 수집하여  
**이메일과 텔레그램**을 통해 실시간 알림을 보냅니다.

---

## 🔔 주요 기능

- 📰 Nexo 관련 최신 Google News 뉴스 수집
- 🐦 트위터(Nitter)를 통한 키워드 감지
- 💹 CoinGecko API를 이용한 실시간 가격 모니터링
- 📉 가격 임계값 하락 시 경고
- 📊 7일간 가격 추이 그래프 자동 생성
- 📬 이메일 및 텔레그램 알림 전송
- 🧠 뉴스 및 트윗 캐시 비교로 중복 제거

---

## 🧪 미리보기

<img src="docs/sample_chart.png" width="500"/>

📊 NEXO Current Price: $1.22
📈 Increase (+1.30%)

📰 News:

Nexo Review 2025: Interest Rates... (Read more)

Crypto Contract Dispute Settled... (Read more)


---

## ⚙️ 설치 및 설정

### 1. 📂 저장소 클론

```bash
git clone https://github.com/your-username/Nexo-Alarm-Bot.git
cd Nexo-Alarm-Bot

2. 🐍 Python 패키지 설치

pip install -r requirements.txt

또는 수동:

pip install feedparser requests beautifulsoup4 matplotlib

3. 📧 Gmail 앱 비밀번호 발급
https://myaccount.google.com/apppasswords

이메일 발신자 계정 설정

4. 🤖 텔레그램 설정
@BotFather로 봇 생성

TOKEN 발급

@userinfobot 으로 chat_id 확인

수신 대상 사용자 또는 그룹에 먼저 메시지를 한 번 보내기

🛠️ GitHub Actions 자동화
.github/workflows/nexo_news_alert.yml는 다음을 수행합니다:

매 6시간마다 자동 실행

GitHub Secrets 설정 필요:

Key	설명
EMAIL_USER	Gmail 주소
EMAIL_PASS	앱 비밀번호
TELEGRAM_TOKEN	BotFather에서 받은 토큰
TELEGRAM_CHAT_ID	알림을 받을 사용자 ID

🚀 수동 실행 (로컬 테스트)
bash
Copy
Edit
python alert_nexo.py
📎 파일 설명
파일명	설명
alert_nexo.py	메인 봇 실행 스크립트
chart.png	자동 생성된 가격 차트 이미지
news_cache.txt	이전 뉴스 캐시
tweet_cache.txt	이전 트윗 캐시
price_cache.txt	가격 변화 기록 (그래프용)
.github/workflows/...	GitHub Actions 워크플로우 자동화 스크립트

🧡 크레딧
이 프로젝트는 오픈소스로 자유롭게 사용 가능합니다.
개선사항 또는 PR 환영합니다!
