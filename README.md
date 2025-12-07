# 🏟️ OlyMate (올리메이트)

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Status](https://img.shields.io/badge/Status-Deployed-success)

> **공연의 감동을 완성하는 가장 스마트한 덕질 파트너** > **2025년도 국민체육진흥공단 공공데이터 활용 경진대회 [서비스 개발 부문] 출품작**

---

## 💡 기획 배경 및 소개
올림픽공원은 국내외 대형 콘서트의 성지이지만, 넓은 부지로 인해 **초행길 관람객들이 편의시설(화장실, 물품보관소)을 찾거나 식사 장소를 정하는 데 어려움**을 겪습니다.

**OlyMate**는 이러한 관람객의 페르소나(Persona)에 맞춰, **공연 당일의 날씨, 티켓 정보, 최적의 동선, 혼잡도를 고려한 맛집 정보**를 올인원으로 제공하는 **AI 기반 관람 가이드 플랫폼**입니다.

## 🚀 주요 기능
* **🤖 AI 시설 가이드 (Smart Agent):** "배고파", "흡연장 어디?" 등 자연어(NLP) 질문 의도를 파악하여, 사용자가 원하는 편의시설 위치를 즉시 찾아 지도에 표시합니다.
* **🗺️ 공연 맞춤형 스마트 맵:** 선택한 공연장(예: KSPO DOME)을 중심으로 지도가 자동 세팅되며, 내 위치 기반 최적의 시설 동선을 시각화합니다.
* **⛅ 실시간 날씨 & D-Day:** 기상청 API와 연동하여 공연 당일의 정확한 날씨 정보와 공연까지 남은 시간을 카운트다운 합니다.
* **🍽️ 데이터 기반 맛집 추천:** 올림픽파크텔 식음료장 이용 데이터를 분석하여, 공연 전후 혼잡하지 않은 최적의 식사 장소를 추천합니다.
* **🌏 글로벌 모드:** 외국인 K-POP 팬덤을 위한 영문(English) 인터페이스를 완벽 지원합니다.

## 🛠️ 활용 공공데이터
| 구분 | 데이터명 | 활용 내용 |
| :--- | :--- | :--- |
| **기상청** | 단기예보 조회 서비스 API | 실시간 기온, 하늘 상태, 강수 확률 조회 |
| **한국체육산업개발** | 올림픽공원 공연 정보 API | 최신 공연 일정, 장소, 기간 데이터 실시간 연동 |
| **국민체육진흥공단** | 올림픽공원 편의시설 정보 | 화장실, 매점 등 160여 개 시설 좌표(위경도) DB화 및 검색 엔진 구축 |
| **국민체육진흥공단** | 올림픽파크텔 이용현황 | 식음료장 및 객실 이용 통계를 분석하여 혼잡도 예측 지표로 활용 |

## 💻 기술 스택 (Tech Stack)
* **Language:** Python 3.11
* **Framework:** Streamlit (Web App)
* **Visualization:** Folium (Interactive Map)
* **Data Processing:** Pandas, NumPy
* **Networking:** Requests (Open API REST call)
* **Logic:** NLP Keyword Mapping Agent, Hybrid Data Fetching (API + Fallback)

## 🔗 서비스 바로가기
👉 **[OlyMate 서비스 체험하기](https://olymate.streamlit.app/)** *(위 링크를 클릭하면 별도의 설치 없이 웹에서 바로 이용 가능합니다.)*

## 📥 설치 및 실행 방법 (Local)
로컬 환경에서 실행하려면 아래 명령어를 순서대로 입력하세요.

```bash
# 1. 저장소 복제
git clone https://github.com/HaimLee-4869/OlyMate.git

# 2. 필수 라이브러리 설치
pip install -r requirements.txt

# 3. API 키 설정 (.streamlit/secrets.toml 생성)
# WEATHER_API_KEY = "..."
# CONCERT_API_KEY = "..."

# 4. 앱 실행
streamlit run app.py