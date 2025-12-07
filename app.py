import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime, timedelta
import json
import re

# ==========================================
# 1. 설정 및 초기화
# ==========================================
st.set_page_config(page_title="OlyMate", layout="wide")

# UI 커스터마이징
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API 키 설정
try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
    CONCERT_API_KEY = st.secrets["CONCERT_API_KEY"]
except FileNotFoundError:
    st.error("API 키를 찾을 수 없습니다. secrets 설정을 확인해주세요.")

# 좌표 설정
NX, NY = 62, 126
VENUE_LOCATIONS = {
    "KSPO DOME": [37.5192018, 127.126537],
    "올림픽체조경기장": [37.5192018, 127.126537],
    "핸드볼경기장": [37.5177339, 127.1257116],
    "올림픽홀": [37.5150613, 127.1271355],
    "우리금융아트홀": [37.5174938, 127.1250809],
    "올림픽공원": [37.5185463, 127.1270634]
}

# Session State 초기화
if 'map_center' not in st.session_state:
    st.session_state['map_center'] = VENUE_LOCATIONS["올림픽공원"]
if 'map_zoom' not in st.session_state:
    st.session_state['map_zoom'] = 16
if 'highlight_marker' not in st.session_state:
    st.session_state['highlight_marker'] = None
if 'language' not in st.session_state:
    st.session_state['language'] = 'Korean'
if 'fan_messages' not in st.session_state:
    st.session_state['fan_messages'] = ["god 오빠들 화이팅!", "성시경 목소리 녹는다.."]

# ==========================================
# 2. 데이터 로드
# ==========================================
@st.cache_data
def load_data():
    try:
        facilities = pd.read_csv("facilities.csv").fillna("")
        users = pd.read_csv("parktel_users.csv").fillna("")
        food = pd.read_csv("parktel_food.csv").fillna("")
    except FileNotFoundError:
        facilities, users, food = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    restaurants = [
        {"name": "빈체로 올림픽공원점", "category": "음식점", "desc": "가성비 좋은 파스타 / Pasta", "lat": 37.515, "lon": 127.122},
        {"name": "제일제면소 올림픽공원점", "category": "음식점", "desc": "넓고 쾌적한 국수집 / Noodle", "lat": 37.517, "lon": 127.129},
        {"name": "몽중헌 방이점", "category": "중식", "desc": "고급스러운 딤섬 맛집 / Chinese Dimsum", "lat": 37.513, "lon": 127.119},
        {"name": "청와옥 본점", "category": "한식", "desc": "줄서서 먹는 순대국 / Korean Soup", "lat": 37.514, "lon": 127.120},
        {"name": "할머니포장마차멸치국수", "category": "국수", "desc": "꼬막과 국수가 맛있는 노포 / Noodle", "lat": 37.512, "lon": 127.118},
        {"name": "안동국시 소담", "category": "한식", "desc": "건강한 한식 / Korean Food", "lat": 37.513, "lon": 127.125},
        {"name": "송도불고기", "category": "BBQ", "desc": "된장찌개 서비스 고기집 / BBQ", "lat": 37.515, "lon": 127.128},
        {"name": "산들해 송파점", "category": "한정식", "desc": "푸짐한 이천쌀밥 한상 / Korean Table", "lat": 37.514, "lon": 127.119},
        {"name": "봉피양 방이점", "category": "BBQ", "desc": "평양냉면과 돼지갈비 / BBQ & Cold Noodle", "lat": 37.511, "lon": 127.123},
        {"name": "프로퍼커피바", "category": "카페", "desc": "분위기 좋은 베이커리 카페 / Bakery Cafe", "lat": 37.510, "lon": 127.124},
        {"name": "투썸플레이스 올림픽공원역점", "category": "카페", "desc": "넓은 좌석 / Spacious Cafe", "lat": 37.516, "lon": 127.130},
        {"name": "스타벅스 올림픽공원남문점", "category": "카페", "desc": "공원 뷰가 좋은 곳 / Park View Cafe", "lat": 37.513, "lon": 127.121},
        {"name": "파리크라상 올림픽공원키친점", "category": "제과점", "desc": "브런치 하기 좋은 곳 / Brunch", "lat": 37.517, "lon": 127.129},
        {"name": "온온커피", "category": "카페", "desc": "수다 떨기 좋은 아늑한 곳 / Cozy Cafe", "lat": 37.522, "lon": 127.133},
        {"name": "애크로매틱 커피", "category": "카페", "desc": "콘센트 많아 작업하기 좋음 / Good for work", "lat": 37.524, "lon": 127.131},
        {"name": "담금 올림픽점", "category": "카페", "desc": "데이트하기 좋은 브런치 카페 / Brunch Date", "lat": 37.523, "lon": 127.132}
    ]
    df_restaurants = pd.DataFrame(restaurants)
    return facilities, users, food, df_restaurants

df_fac, df_users, df_food, df_rest = load_data()

# ==========================================
# 3. Agent 클래스 (영어 지원 업그레이드)
# ==========================================
class SmartAgent:
    def __init__(self, fac_df, rest_df):
        self.fac_df = fac_df
        self.rest_df = rest_df
        # 한글 및 영어 동의어 사전 (소문자 기준)
        self.synonyms = {
            # 시설 (한글)
            "물": "음수대", "물마시는곳": "음수대", "식수": "음수대",
            "화장실": "화장실", "변소": "화장실",
            "담배": "흡연구역", "흡연": "흡연구역", "흡연장": "흡연구역",
            "쓰레기": "쓰레기통", "휴지통": "쓰레기통",
            "음료수": "자판기", "과자": "자판기",
            "밥": "식음료판매점", "식당": "식음료판매점", 
            
            # Facility (English Mapping to Korean Data)
            "toilet": "화장실", "restroom": "화장실", "wc": "화장실", "bathroom": "화장실",
            "store": "편의점", "convenience": "편의점", "cvs": "편의점", "shop": "편의점",
            "smoking": "흡연구역", "smoke": "흡연구역", "cigarette": "흡연구역", "area": "흡연구역", # Smoking Area 처리
            "trash": "쓰레기통", "bin": "쓰레기통", "can": "쓰레기통", "rubbish": "쓰레기통",
            "vending": "자판기", "machine": "자판기",
            "food": "식음료판매점", "court": "식음료판매점", "snack": "식음료판매점",
            "water": "음수대", "drinking": "음수대", "fountain": "음수대", "drink": "음수대"
        }

    def search_facility(self, user_query):
        # 입력값 소문자 변환 및 특수문자 제거
        clean_query = re.sub(r'[^\w\s]', '', user_query).strip().lower()
        tokens = clean_query.split()
        target_keyword = None
        
        for token in tokens:
            # 1. 동의어 사전 매칭 (영어/한글 모두)
            if token in self.synonyms:
                target_keyword = self.synonyms[token]
                break
            # 2. 데이터프레임 내 직접 매칭 (한글 검색용)
            if any(self.fac_df['구분'].str.contains(token)):
                target_keyword = token
                break
        
        search_term = target_keyword if target_keyword else clean_query
        results = self.fac_df[self.fac_df['구분'].str.contains(search_term) | self.fac_df['상세위치'].str.contains(search_term)]
        return results, search_term

    def recommend_place(self, user_query):
        q = user_query.lower() # 소문자 변환
        keywords = q.split()
        mask = pd.Series([False] * len(self.rest_df))
        
        for k in keywords:
            # 영어 설명(desc) 검색 지원을 위해 desc도 검색 대상에 포함
            mask |= self.rest_df['name'].str.lower().str.contains(k) | \
                    self.rest_df['category'].str.lower().str.contains(k) | \
                    self.rest_df['desc'].str.lower().str.contains(k)
        
        # 의도 파악 (영어 키워드 추가)
        hungry_keywords = ["배고파", "밥", "맛집", "hungry", "rice", "meal", "restaurant", "food", "lunch", "dinner"]
        cafe_keywords = ["목말라", "커피", "카페", "cafe", "coffee", "tea", "thirsty", "quiet"]
        
        if any(x in q for x in hungry_keywords):
            mask |= self.rest_df['category'].isin(["음식점", "한식", "중식", "국수", "BBQ", "한정식"])
        if any(x in q for x in cafe_keywords):
            mask |= self.rest_df['category'].isin(["카페", "제과점"])
            
        return self.rest_df[mask]

agent = SmartAgent(df_fac, df_rest)

# ==========================================
# 4. API & Utils
# ==========================================
def get_weather():
    now = datetime.now()
    if now.minute < 45: now = now - timedelta(hours=1)
    times = [2, 5, 8, 11, 14, 17, 20, 23]
    base_hour = max([t for t in times if t <= now.hour] or [23])
    base_date = now.strftime("%Y%m%d")
    base_time = f"{base_hour:02d}00"
    if now.hour < 2:
        yesterday = now - timedelta(days=1)
        base_date = yesterday.strftime("%Y%m%d")
        base_time = "2300"

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {"serviceKey": WEATHER_API_KEY, "pageNo": "1", "numOfRows": "100", "dataType": "JSON", "base_date": base_date, "base_time": base_time, "nx": NX, "ny": NY}
    
    try:
        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        items = data['response']['body']['items']['item']
        weather_info = {"TMP": "-", "SKY": "-", "POP": "-"}
        target_time = items[0]['fcstTime']
        for item in items:
            if item['fcstTime'] == target_time:
                if item['category'] == 'TMP': weather_info['TMP'] = item['fcstValue']
                if item['category'] == 'SKY': 
                    code = int(item['fcstValue'])
                    weather_info['SKY'] = "맑음 ☀️" if code == 1 else "구름많음 ⛅" if code == 3 else "흐림 ☁️"
                if item['category'] == 'POP': weather_info['POP'] = item['fcstValue']
        return weather_info
    except Exception:
        return None

def get_concert_list():
    return [
        {"title": "2025 god CONCERT <ICONIC BOX>", "date": "2025-12-05 ~ 07", "place": "KSPO DOME", "link": "https://www.ticketlink.co.kr/product/58697"},
        {"title": "2025 정승환의 안녕, 겨울", "date": "2025-12-05 ~ 07", "place": "핸드볼경기장", "link": "https://tickets.interpark.com/goods/25013763"},
        {"title": "가족뮤지컬 〈호두까기인형〉", "date": "2025-12-06 ~ 01-25", "place": "우리금융아트홀", "link": "https://tickets.interpark.com/goods/25010991"},
        {"title": "2025 손태진 전국투어 콘서트", "date": "2025-12-06 ~ 2025-12-07", "place": "올림픽홀", "link": "https://tickets.interpark.com/goods/25015666"},
        {"title": "2025 이문세 ‘The Best’", "date": "2025-12-13 ~ 14", "place": "KSPO DOME", "link": "https://tickets.interpark.com/goods/25012678"},
        {"title": "2025 N.Flying LIVE 'Let’s Roll'", "date": "2025-12-19 ~ 2025-12-21", "place": "올림픽핸드볼경기장", "link": "https://ticket.melon.com/performance/index.htm?prodId=212207"},
        {"title": "2025 DAY6 Special Concert", "date": "2025-12-19 ~ 2025-12-21", "place": "KSPO DOME", "link": "https://ticket.yes24.com/Special/55971"},
        {"title": "2025 규현(KYUHYUN) Concert", "date": "2025-12-19 ~ 2025-12-21", "place": "올림픽홀", "link": "https://tickets.interpark.com/goods/25014743"},
        {"title": "2025 성시경 연말 콘서트", "date": "2025-12-25 ~ 28", "place": "KSPO DOME", "link": "https://tickets.interpark.com/goods/25016342"},
        {"title": "2025 에픽하이 콘서트", "date": "2025-12-25 ~ 28", "place": "올림픽핸드볼경기장", "link": "https://tickets.interpark.com/goods/25014649"}
    ]

# ==========================================
# 5. 사이드바
# ==========================================
with st.sidebar:
    st.header("🏟️ OlyMate")
    st.title("⚙️ 설정 (Settings)")
    lang = st.radio("Language / 언어", ["Korean", "English"])
    st.session_state['language'] = lang
    st.markdown("---")
    st.info("💡 **OlyMate**는 공공데이터를 활용하여 관람객에게 최적의 경험을 제공합니다.")
    st.caption("Data: 국민체육진흥공단, 기상청, 한국체육산업개발")

TEXT = {
    "Korean": {
        "title": "🏟️ OlyMate (올리메이트)",
        "subtitle": "**공연의 감동을 완성하는 가장 스마트한 덕질 파트너**",
        "weather_header": "🌤️ 날씨",
        "temp_label": "현재 기온",
        "err_weather": "기상청 API 연결 실패 (키 확인 필요)",
        "err_weather_caption": "현재 기온 정보를 가져올 수 없습니다.",
        "concert_header": "🎫 공연 선택",
        "concert_msg": "🎵 **'{title}'** 관람을 환영합니다!",
        "date_label": "📅 일시: {date} | 📍 장소: {place}",
        "btn_link": "🎟️ 예매처 / 상세정보 확인하기",
        "d_day_header": "🗓️ D-Day",
        "d_minus": "공연까지",
        "d_ing": "진행중 🎤",
        "tabs": ["💬 시설 가이드", "🍽️ 맛집/카페", "🗺️ 스마트 맵", "📊 혼잡도 분석", "📢 팬 존"],
        "tab1_header": "🤖 공원 시설 AI 가이드",
        "tab1_desc": "공원 내부 편의시설을 찾아드립니다. (예: 화장실, 편의점, 흡연구역, 쓰레기통, 자판기, 식음료판매점, 음수대)",
        "tab1_input": "시설 질문 입력",
        "tab1_res_fmt": "'{keyword}' 관련 시설 {count}개 발견",
        "btn_map": "지도 보기",
        "btn_loc": "위치 보기",
        "btn_nav": "길찾기 ↗️",
        "toast_msg": "상단 '스마트 맵' 탭을 눌러주세요! 🗺️",
        "warn_no_res": "관련 시설을 찾지 못했습니다.",
        "tab2_header": "🍽️ 맛집/카페 추천",
        "tab2_input": "맛집 질문 입력 (예: 조용한 카페, 배고파, 밥집)",
        "tab2_success": "추천 장소 {count}곳을 찾았습니다!",
        "warn_no_food": "조건에 맞는 추천 장소가 없습니다.",
        "tab3_caption": "✅ 체크박스를 눌러 주변 시설을 한눈에 확인하세요.",
        "filter_wc": "화장실", "filter_cvs": "편의점", "filter_food": "맛집",
        "filter_smoke": "흡연장", "filter_vending": "자판기", "filter_water": "음수대",
        "parking_header": "🚗 주차 및 교통 정보 보기",
        "parking_body": """
        - **가까운 주차장:** P5 (KSPO DOME 맞은편), P6 (SK핸드볼경기장 뒤)
        - **주차 요금:** 소형 10분당 600원 / 대형 10분당 1,200원 (공연 관람객 할인 없음)
        - **지하철:** 5호선/9호선 올림픽공원역 3번, 4번 출구
        """,
        "tab4_header": "📊 빅데이터로 본 혼잡도 예측",
        "tab4_msg1": "🏢 **숙박/식당:** 공연 종료 후 1시간 동안은 식당가가 매우 혼잡합니다.",
        "tab4_msg2": "🌏 **방문객:** 최근 외국인 관람객 비율이 증가 추세입니다.",
        "tab5_header": "📢 Fan Zone",
        "tab5_desc": "공연을 기다리며 응원의 메시지를 남겨보세요!",
        "msg_input": "메시지 입력",
        "msg_btn": "응원하기 🚀",
        "msg_toast": "메시지가 등록되었습니다!",
        "footer_caption": "© 2025 OlyMate Team | 국민체육진흥공단 공공데이터 활용 | Developed by Streamlit"
    },
    "English": {
        "title": "🏟️ OlyMate (OlyMate)",
        "subtitle": "**The Smartest Partner for Your Concert Experience**",
        "weather_header": "🌤️ Weather",
        "temp_label": "Temperature",
        "err_weather": "Weather API Connection Failed",
        "err_weather_caption": "Cannot retrieve weather info.",
        "concert_header": "🎫 Select Concert",
        "concert_msg": "🎵 Welcome to **'{title}'**!",
        "date_label": "📅 Date: {date} | 📍 Venue: {place}",
        "btn_link": "🎟️ Ticket / Details",
        "d_day_header": "🗓️ D-Day",
        "d_minus": "D-Day",
        "d_ing": "Live Now 🎤",
        "tabs": ["💬 Facility Guide", "🍽️ Food & Cafe", "🗺️ Smart Map", "📊 Analytics", "📢 Fan Zone"],
        "tab1_header": "🤖 AI Facility Guide",
        "tab1_desc": "Find facilities inside the park. (e.g., Toilet, Store, Smoking Area, Trash Can, Vending Machine, Food Court, Drinking Fountain)",
        "tab1_input": "Search Facility",
        "tab1_res_fmt": "Found {count} facilities related to '{keyword}'",
        "btn_map": "View Map",
        "btn_loc": "View Loc",
        "btn_nav": "Navi ↗️",
        "toast_msg": "Go to 'Smart Map' tab! 🗺️",
        "warn_no_res": "No related facilities found.",
        "tab2_header": "🍽️ Food/Cafe Recommendation",
        "tab2_input": "Ask food (e.g., Quiet cafe, Hungry, Rice)",
        "tab2_success": "Found {count} recommended places!",
        "warn_no_food": "No places found matching your condition.",
        "tab3_caption": "✅ Check boxes to see facilities on the map.",
        "filter_wc": "Toilet", "filter_cvs": "Store", "filter_food": "Food",
        "filter_smoke": "Smoking", "filter_vending": "Vending", "filter_water": "Water",
        "parking_header": "🚗 Parking & Traffic Info",
        "parking_body": """
        - **Parking:** P5 (Opposite KSPO DOME), P6 (Behind Handball Stadium)
        - **Fee:** Small 600 KRW / 10min, Large 1,200 KRW / 10min (No discount for concert)
        - **Subway:** Line 5/9 Olympic Park Station Exit 3, 4
        """,
        "tab4_header": "📊 Crowd Analytics by Big Data",
        "tab4_msg1": "🏢 **Food/Stay:** Restaurants are very crowded for 1 hour after the concert.",
        "tab4_msg2": "🌏 **Visitors:** The ratio of foreign visitors is increasing recently.",
        "tab5_header": "📢 Fan Zone",
        "tab5_desc": "Leave a cheering message while waiting!",
        "msg_input": "Enter message",
        "msg_btn": "Submit 🚀",
        "msg_toast": "Message posted!",
        "footer_caption": "© 2025 OlyMate Team | KSPO Public Data Usage | Developed by Streamlit"
    }
}
T = TEXT[st.session_state['language']]

# ==========================================
# 6. 메인 UI
# ==========================================
st.title(T["title"])
st.markdown(T["subtitle"])

concerts = get_concert_list()
weather = get_weather()

m1, m2, m3 = st.columns([1, 2, 1])

with m1:
    st.subheader(T["weather_header"])
    if weather:
        st.metric(T["temp_label"], f"{weather['TMP']}°C", weather['SKY'])
    else:
        st.error(T["err_weather"])
        st.caption(T["err_weather_caption"])

with m2:
    st.subheader(T["concert_header"])
    c_titles = [c['title'] for c in concerts]
    sel_title = st.selectbox("Label hidden", c_titles, label_visibility="collapsed")
    sel_concert = next(c for c in concerts if c['title'] == sel_title)
    
    st.success(T["concert_msg"].format(title=sel_title))
    
    # [수정됨] 중복 버튼 제거 및 텍스트 표시
    st.write(T["date_label"].format(date=sel_concert['date'], place=sel_concert['place']))

    if st.session_state.get('last_concert') != sel_title:
        center = VENUE_LOCATIONS.get("올림픽공원")
        for k, v in VENUE_LOCATIONS.items():
            if k in sel_concert['place']: center = v
        st.session_state['map_center'] = center
        st.session_state['last_concert'] = sel_title
        st.session_state['highlight_marker'] = None

with m3:
    st.subheader(T["d_day_header"])
    d_day = (datetime.strptime(sel_concert['date'].split("~")[0].strip(), "%Y-%m-%d") - datetime.now()).days
    if d_day > 0:
        st.metric(T["d_minus"], f"D-{d_day}")
    else:
        st.metric("Status", T["d_ing"], delta_color="inverse")

with st.container():
    st.markdown(f"""
    <div style="background-color:#e8f4f8; padding:15px; border-radius:10px; border-left: 5px solid #00a8cc;">
        <h4>🎵 {sel_title}</h4>
        <p>📍 <b>Location:</b> {sel_concert['place']} &nbsp; | &nbsp; 📅 <b>Date:</b> {sel_concert['date']}</p>
    </div>
    """, unsafe_allow_html=True)
    st.link_button(T["btn_link"], sel_concert['link'], use_container_width=True)

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(T["tabs"])

# --- TAB 1: 시설 가이드 ---
with tab1:
    st.header(T["tab1_header"])
    st.markdown(T["tab1_desc"])
    # [재수정] 언어가 영어면 라벨을 숨기고(collapsed), 한국어면 보이게(visible) 설정
    label_vis = "collapsed" if st.session_state['language'] == 'English' else "visible"
    
    # 딕셔너리에 글자가 있어도 label_visibility가 collapsed면 화면엔 안 보임 (에러 해결)
    fac_query = st.text_input(T["tab1_input"], key="fac_input", label_visibility=label_vis)
    if fac_query:
        results, keyword = agent.search_facility(fac_query)
        if not results.empty:
            st.success(T["tab1_res_fmt"].format(keyword=keyword, count=len(results)))
            for idx, row in results.iterrows():
                loc_text = f"{row['구분']}" + (f" ({row['상세위치']})" if row['상세위치'] else "")
                c1, c2 = st.columns([4, 1])
                with c1: st.info(f"📍 {loc_text} (위치: {row['위치']})")
                with c2:
                    if st.button(T["btn_map"], key=f"fac_{idx}"):
                        st.session_state['map_center'] = [row['위도'], row['경도']]
                        st.session_state['map_zoom'] = 18
                        st.session_state['highlight_marker'] = {"loc": [row['위도'], row['경도']], "popup": loc_text, "color": "blue"}
                        st.toast(T["toast_msg"], icon="✅")
        else:
            st.warning(T["warn_no_res"])

# --- TAB 2: 맛집 추천 ---
with tab2:
    st.header(T["tab2_header"])
    food_query = st.text_input(T["tab2_input"], key="food_input")
    if food_query:
        recs = agent.recommend_place(food_query)
        if not recs.empty:
            st.success(T["tab2_success"].format(count=len(recs)))
            for idx, row in recs.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1: 
                    st.write(f"**{row['name']}** ({row['category']})")
                    st.caption(f"📝 {row['desc']}")
                with c2:
                    if st.button(T["btn_loc"], key=f"rest_{idx}"):
                        st.session_state['map_center'] = [row['lat'], row['lon']]
                        st.session_state['map_zoom'] = 17
                        st.session_state['highlight_marker'] = {"loc": [row['lat'], row['lon']], "popup": row['name'], "color": "green"}
                        st.toast(T["toast_msg"], icon="✅")
                with c3:
                    naver_map_url = f"https://map.naver.com/v5/search/{row['name']}"
                    st.link_button(T["btn_nav"], naver_map_url) 
        else:
            st.warning(T["warn_no_food"])

# --- TAB 3: 스마트 맵 ---
with tab3:
    st.caption(T["tab3_caption"])
    cols = st.columns(6)
    filters = {
        T["filter_wc"]: cols[0].checkbox(T["filter_wc"]),
        T["filter_cvs"]: cols[1].checkbox(T["filter_cvs"]),
        T["filter_food"]: cols[2].checkbox(T["filter_food"]),
        T["filter_smoke"]: cols[3].checkbox(T["filter_smoke"]),
        T["filter_vending"]: cols[4].checkbox(T["filter_vending"]),
        T["filter_water"]: cols[5].checkbox(T["filter_water"])
    }

    m = folium.Map(location=st.session_state['map_center'], zoom_start=st.session_state['map_zoom'])
    venue_loc = VENUE_LOCATIONS.get("올림픽공원")
    for k, v in VENUE_LOCATIONS.items():
        if k in sel_concert['place']: venue_loc = v
    folium.Marker(venue_loc, popup=folium.Popup(f"<b>{sel_concert['place']}</b>", min_width=200, max_width=300), icon=folium.Icon(color='red', icon='star')).add_to(m)

    if st.session_state['highlight_marker']:
        hm = st.session_state['highlight_marker']
        folium.Marker(hm['loc'], popup=folium.Popup(hm['popup'], min_width=200, max_width=300), icon=folium.Icon(color=hm.get('color', 'blue'), icon='info-sign')).add_to(m)

    map_keywords = {
        T["filter_wc"]: "화장실", T["filter_cvs"]: "편의점", T["filter_food"]: "맛집",
        T["filter_smoke"]: "흡연", T["filter_vending"]: "자판기", T["filter_water"]: "음수대"
    }

    for label, checked in filters.items():
        if checked:
            search_key = map_keywords[label]
            if search_key == "맛집":
                for _, row in df_rest.iterrows():
                    folium.Marker([row['lat'], row['lon']], popup=folium.Popup(f"<b>{row['name']}</b><br>{row['desc']}", min_width=200, max_width=300), icon=folium.Icon(color='green', icon='cutlery')).add_to(m)
            else:
                subset = df_fac[df_fac['구분'].str.contains(search_key)]
                for _, row in subset.iterrows():
                    name = f"{row['구분']}" + (f" ({row['상세위치']})" if row['상세위치'] else "")
                    folium.Marker([row['위도'], row['경도']], popup=folium.Popup(name, min_width=200, max_width=300), icon=folium.Icon(color='blue', icon='cloud')).add_to(m)

    st_folium(m, width=1400, height=600, key="main_map")
    
    with st.expander(T["parking_header"], expanded=True):
        st.markdown(T["parking_body"])

# --- TAB 4: 데이터 분석 ---
with tab4:
    st.markdown(f"### {T['tab4_header']}")
    c1, c2 = st.columns(2)
    with c1: 
        st.success(T["tab4_msg1"])
        if not df_food.empty: st.line_chart(df_food.set_index('구분')[['한식당', '커피숍']])
    with c2: 
        st.info(T["tab4_msg2"])
        if not df_users.empty: st.bar_chart(df_users.set_index('구분')[['일반내국인', '일반외국인']])

# --- TAB 5: 팬 존 ---
with tab5:
    st.header(T["tab5_header"])
    st.markdown(T["tab5_desc"])
    with st.form("fan_form", clear_on_submit=True):
        msg = st.text_input(T["msg_input"])
        submitted = st.form_submit_button(T["msg_btn"])
        if submitted and msg:
            st.session_state['fan_messages'].insert(0, msg)
            st.toast(T["msg_toast"], icon="✅")
    for m in st.session_state['fan_messages']:
        st.write(f"💬 {m}")

# Footer
st.markdown("---")
st.caption(T["footer_caption"])