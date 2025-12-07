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



# UI 커스터마이징 (카드 스타일, 버튼 등)
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
# API 키 설정 (Streamlit Secrets에서 불러오기)
# 로컬에서는 .streamlit/secrets.toml을 읽고, 배포 후에는 Cloud 설정을 읽음
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
# 2. 데이터 로드 (맛집 목업 데이터 포함)
# ==========================================
@st.cache_data
def load_data():
    try:
        facilities = pd.read_csv("facilities.csv").fillna("")
        users = pd.read_csv("parktel_users.csv").fillna("")
        food = pd.read_csv("parktel_food.csv").fillna("")
    except FileNotFoundError:
        facilities, users, food = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # [NEW] 맛집/카페 목업 데이터 (사용자 제공)
    restaurants = [
        {"name": "빈체로 올림픽공원점", "category": "음식점", "desc": "가성비 좋은 파스타", "lat": 37.515, "lon": 127.122},
        {"name": "제일제면소 올림픽공원점", "category": "음식점", "desc": "넓고 쾌적한 국수집", "lat": 37.517, "lon": 127.129},
        {"name": "몽중헌 방이점", "category": "중식", "desc": "고급스러운 딤섬 맛집", "lat": 37.513, "lon": 127.119},
        {"name": "청와옥 본점", "category": "한식", "desc": "줄서서 먹는 순대국", "lat": 37.514, "lon": 127.120},
        {"name": "할머니포장마차멸치국수", "category": "국수", "desc": "꼬막과 국수가 맛있는 노포", "lat": 37.512, "lon": 127.118},
        {"name": "안동국시 소담", "category": "한식", "desc": "건강한 한식", "lat": 37.513, "lon": 127.125},
        {"name": "송도불고기", "category": "BBQ", "desc": "된장찌개 서비스 고기집", "lat": 37.515, "lon": 127.128},
        {"name": "산들해 송파점", "category": "한정식", "desc": "푸짐한 이천쌀밥 한상", "lat": 37.514, "lon": 127.119},
        {"name": "봉피양 방이점", "category": "BBQ", "desc": "평양냉면과 돼지갈비", "lat": 37.511, "lon": 127.123},
        
        {"name": "프로퍼커피바", "category": "카페", "desc": "분위기 좋은 베이커리 카페", "lat": 37.510, "lon": 127.124},
        {"name": "투썸플레이스 올림픽공원역점", "category": "카페", "desc": "넓은 좌석", "lat": 37.516, "lon": 127.130},
        {"name": "스타벅스 올림픽공원남문점", "category": "카페", "desc": "공원 뷰가 좋은 곳", "lat": 37.513, "lon": 127.121},
        {"name": "파리크라상 올림픽공원키친점", "category": "제과점", "desc": "브런치 하기 좋은 곳", "lat": 37.517, "lon": 127.129},
        {"name": "온온커피", "category": "카페", "desc": "수다 떨기 좋은 아늑한 곳", "lat": 37.522, "lon": 127.133},
        {"name": "애크로매틱 커피", "category": "카페", "desc": "콘센트 많아 작업하기 좋음", "lat": 37.524, "lon": 127.131},
        {"name": "담금 올림픽점", "category": "카페", "desc": "데이트하기 좋은 브런치 카페", "lat": 37.523, "lon": 127.132}
    ]
    df_restaurants = pd.DataFrame(restaurants)
    
    return facilities, users, food, df_restaurants

df_fac, df_users, df_food, df_rest = load_data()

# ==========================================
# 3. Agent 클래스 (시설 + 맛집 통합)
# ==========================================
class SmartAgent:
    def __init__(self, fac_df, rest_df):
        self.fac_df = fac_df
        self.rest_df = rest_df
        self.synonyms = {
            "물": "음수대", "물마시는곳": "음수대", "식수": "음수대",
            "화장실": "화장실", "변소": "화장실",
            "담배": "흡연구역", "흡연": "흡연구역", "흡연장": "흡연구역", # 동의어 보강
            "쓰레기": "쓰레기통", "휴지통": "쓰레기통",
            "음료수": "자판기", "과자": "자판기"
        }

    def search_facility(self, user_query):
        clean_query = re.sub(r'[^\w\s]', '', user_query).strip()
        tokens = clean_query.split()
        target_keyword = None
        
        for token in tokens:
            if token in self.synonyms:
                target_keyword = self.synonyms[token]
                break
            if any(self.fac_df['구분'].str.contains(token)):
                target_keyword = token
                break
        
        search_term = target_keyword if target_keyword else clean_query
        results = self.fac_df[self.fac_df['구분'].str.contains(search_term) | self.fac_df['상세위치'].str.contains(search_term)]
        return results, search_term

    def recommend_place(self, user_query):
        # 간단한 키워드 매칭 추천
        keywords = user_query.split()
        mask = pd.Series([False] * len(self.rest_df))
        
        for k in keywords:
            mask |= self.rest_df['name'].str.contains(k) | self.rest_df['category'].str.contains(k) | self.rest_df['desc'].str.contains(k)
        
        if "배고파" in user_query or "밥" in user_query or "맛집" in user_query:
            mask |= self.rest_df['category'].isin(["음식점", "한식", "중식", "국수", "BBQ", "한정식"])
        if "목말라" in user_query or "커피" in user_query or "카페" in user_query:
            mask |= self.rest_df['category'].isin(["카페", "제과점"])
            
        return self.rest_df[mask]

agent = SmartAgent(df_fac, df_rest)

# ==========================================
# 4. API & Mock Data 함수
# ==========================================
def get_weather():
    """기상청 API 연동 (실시간)"""
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
    params = {
        "serviceKey": WEATHER_API_KEY, 
        "pageNo": "1", "numOfRows": "100", "dataType": "JSON",
        "base_date": base_date, "base_time": base_time, "nx": NX, "ny": NY
    }
    
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
        # API 실패 시 None 반환 (가짜 데이터 표시 X)
        return None



def get_concert_list():

    """API와 공식 일정을 병합하여 공연 리스트 반환 (하이브리드)"""

    # 1. 2025년 12월 공식 일정 (우선순위)

    concert_list = [

        {"title": "2025 god CONCERT <ICONIC BOX>", "date": "2025-12-05 ~ 2025-12-07", "place": "KSPO DOME", "link": "https://www.ticketlink.co.kr/product/58697"},

        {"title": "2025 정승환의 안녕, 겨울", "date": "2025-12-05 ~ 2025-12-07", "place": "올림픽핸드볼경기장", "link": "https://tickets.interpark.com/goods/25013763"},

        {"title": "가족뮤지컬 〈호두까기인형〉", "date": "2025-12-06 ~ 2026-01-25", "place": "우리금융아트홀", "link": "https://tickets.interpark.com/goods/25010991"},

        {"title": "2025 손태진 전국투어 콘서트", "date": "2025-12-06 ~ 2025-12-07", "place": "올림픽홀", "link": "https://tickets.interpark.com/goods/25015666"},

        {"title": "2025 이문세 ‘The Best’", "date": "2025-12-13 ~ 2025-12-14", "place": "KSPO DOME", "link": "https://tickets.interpark.com/goods/25012678"},

        {"title": "2025 N.Flying LIVE 'Let’s Roll'", "date": "2025-12-19 ~ 2025-12-21", "place": "올림픽핸드볼경기장", "link": "https://ticket.melon.com/performance/index.htm?prodId=212207"},

        {"title": "2025 DAY6 Special Concert", "date": "2025-12-19 ~ 2025-12-21", "place": "KSPO DOME", "link": "https://ticket.yes24.com/Special/55971"},

        {"title": "2025 규현(KYUHYUN) Concert", "date": "2025-12-19 ~ 2025-12-21", "place": "올림픽홀", "link": "https://tickets.interpark.com/goods/25014743"},

        {"title": "2025 성시경 연말 콘서트", "date": "2025-12-25 ~ 2025-12-28", "place": "KSPO DOME", "link": "https://tickets.interpark.com/goods/25016342"},

        {"title": "2025 에픽하이 콘서트", "date": "2025-12-25 ~ 2025-12-28", "place": "올림픽핸드볼경기장", "link": "https://tickets.interpark.com/goods/25014649"}

    ]

   

    # 2. API 호출 (보조)

    url = "https://api.kcisa.kr/openapi/service/rest/meta/KSCperf"

    params = {

        "serviceKey": CONCERT_API_KEY,

        "numOfRows": "50",

        "pageNo": "1",

        "keyword": "2025"

    }

    headers = {"accept": "application/json"}

   

    try:

        response = requests.get(url, params=params, headers=headers, timeout=2)

        if response.status_code == 200:

            data = response.json()

            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])

            if isinstance(items, dict): items = [items]

           

            for item in items:

                if not any(c['title'] == item.get('title') for c in concert_list):

                    if "2025" in item.get('temporalCoverage', ''):

                        concert_list.append({

                            "title": item.get('title'),

                            "date": item.get('temporalCoverage'),

                            "place": item.get('spatial')

                        })

    except:

        pass



    return concert_list


# ==========================================
# 5. 사이드바 (설정)
# ==========================================
with st.sidebar:
    st.header("🏟️ OlyMate")
    st.title("⚙️ 설정 (Settings)")
    
    # 다국어 모드 (발전가능성 어필)
    lang = st.radio("Language / 언어", ["Korean", "English"])
    st.session_state['language'] = lang
    
    st.markdown("---")
    st.info("💡 **OlyMate**는 공공데이터를 활용하여 관람객에게 최적의 경험을 제공합니다.")
    st.caption("Data: 국민체육진흥공단, 기상청, 한국체육산업개발")

# 언어 설정 딕셔너리
TEXT = {
    "Korean": {"title": "🏟️ OlyMate", "weather": "실시간 날씨", "select": "🎫 공연 선택", "welcome": "관람을 환영합니다!", "tabs": ["💬 시설 가이드", "🍽️ 맛집/카페", "🗺️ 스마트 맵", "📊 혼잡도 분석", "📢 팬 존"]},
    "English": {"title": "🏟️ OlyMate", "weather": "Weather", "select": "Select Concert", "welcome": "Welcome to the show!", "tabs": ["💬 Facility Guide", "🍽️ Food & Cafe", "🗺️ Smart Map", "📊 Analytics", "📢 Fan Zone"]}
}
T = TEXT[st.session_state['language']]



# ==========================================
# 5. UI 구성
st.title(T["title"])
st.markdown("**공연의 감동을 완성하는 가장 스마트한 덕질 파트너**")

concerts = get_concert_list()
weather = get_weather()

# 상단 대시보드 (3단 레이아웃)
m1, m2, m3 = st.columns([1, 2, 1])

with m1:
    st.subheader("🌤️ 날씨")
    if weather:
        st.metric("현재 기온", f"{weather['TMP']}°C", weather['SKY'])
    else:
        st.error("기상청 API 연결 실패 (키 확인 필요)")
        st.caption("현재 기온 정보를 가져올 수 없습니다.")

with m2:
    st.subheader("🎫 공연 선택")
    c_titles = [c['title'] for c in concerts]
    sel_title = st.selectbox("Label hidden", c_titles, label_visibility="collapsed")
    sel_concert = next(c for c in concerts if c['title'] == sel_title)
    
    # 공연 선택 반응형 메시지
    st.success(f"🎵 **'{sel_title}'** 관람을 환영합니다!")
    c_info1, c_info2 = st.columns([3, 1])
    with c_info1:
        st.write(f"📅 일시: {sel_concert['date']} | 📍 장소: {sel_concert['place']}")


    # 지도 중심 이동
    if st.session_state.get('last_concert') != sel_title:
        center = VENUE_LOCATIONS.get("올림픽공원")
        for k, v in VENUE_LOCATIONS.items():
            if k in sel_concert['place']: center = v
        st.session_state['map_center'] = center
        st.session_state['last_concert'] = sel_title
        st.session_state['highlight_marker'] = None

with m3:
    st.subheader("🗓️ D-Day")
    # 간단한 날짜 계산 Mock
    d_day = (datetime.strptime(sel_concert['date'].split("~")[0].strip(), "%Y-%m-%d") - datetime.now()).days
    if d_day > 0:
        st.metric("공연까지", f"D-{d_day}")
    else:
        st.metric("상태", "진행중 🎤", delta_color="inverse")

# 공연 상세 정보 카드
with st.container():
    st.markdown(f"""
    <div style="background-color:#e8f4f8; padding:15px; border-radius:10px; border-left: 5px solid #00a8cc;">
        <h4>🎵 {sel_title}</h4>
        <p>📍 <b>장소:</b> {sel_concert['place']} &nbsp; | &nbsp; 📅 <b>일시:</b> {sel_concert['date']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 예매 링크 버튼
    st.link_button("🎟️ 예매처 / 상세정보 확인하기", sel_concert['link'], use_container_width=True)

st.divider()

# 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs(T["tabs"])

# --- TAB 1: 시설 가이드 ---
with tab1:
    st.header("🤖 공원 시설 AI 가이드")
    
    st.markdown("공원 내부 편의시설을 찾아드립니다. (예: 화장실, 편의점, 흡연구역, 쓰레기통, 자판기, 식음료판매점, 음수대)")
    
    fac_query = st.text_input("시설 질문 입력", key="fac_input")
    if fac_query:
        results, keyword = agent.search_facility(fac_query)
        if not results.empty:
            st.success(f"'{keyword}' 관련 시설 {len(results)}개 발견")
            for idx, row in results.iterrows():
                loc_text = f"{row['구분']}" + (f" ({row['상세위치']})" if row['상세위치'] else "")
                c1, c2 = st.columns([4, 1])
                with c1: st.info(f"📍 {loc_text} (위치: {row['위치']})")
                with c2:
                    if st.button("지도 보기", key=f"fac_{idx}"):
                        st.session_state['map_center'] = [row['위도'], row['경도']]
                        st.session_state['map_zoom'] = 18
                        st.session_state['highlight_marker'] = {"loc": [row['위도'], row['경도']], "popup": loc_text, "color": "blue"}
                        st.toast("상단 '스마트 맵' 탭을 눌러주세요! 🗺️", icon="✅")
        else:
            st.warning("관련 시설을 찾지 못했습니다.")

# --- TAB 2: 맛집 추천 ---
# --- TAB 2: 맛집 추천 ---
with tab2:
    st.header("🍽️ 맛집/카페 추천")
    food_query = st.text_input("맛집 질문 입력 (예: 조용한 카페, 배고파, 밥집)", key="food_input")
    
    if food_query:
        recs = agent.recommend_place(food_query)
        if not recs.empty:
            st.success(f"추천 장소 {len(recs)}곳을 찾았습니다!")
            for idx, row in recs.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1]) # 컬럼을 3개로 나눔
                
                with c1: 
                    st.write(f"**{row['name']}** ({row['category']})")
                    st.caption(f"📝 {row['desc']}")
                
                with c2:
                    # 기존: 앱 내 지도 이동
                    if st.button("위치 보기", key=f"rest_{idx}"):
                        st.session_state['map_center'] = [row['lat'], row['lon']]
                        st.session_state['map_zoom'] = 17
                        st.session_state['highlight_marker'] = {"loc": [row['lat'], row['lon']], "popup": row['name'], "color": "green"}
                        st.toast("상단 '스마트 맵' 탭으로 이동하세요! 🗺️", icon="✅")
                
                with c3:
                    # [NEW] 네이버 지도 검색 링크 생성 (실용성 UP)
                    # 모바일에서도 바로 네이버 지도가 열립니다.
                    naver_map_url = f"https://map.naver.com/v5/search/{row['name']}"
                    st.link_button("길찾기 ↗️", naver_map_url) 
        else:
            st.warning("조건에 맞는 추천 장소가 없습니다.")

# --- TAB 3: 스마트 맵 (업그레이드) ---
# --- TAB 3: 스마트 맵 (풀 기능) ---
with tab3:
    st.caption("✅ 체크박스를 눌러 주변 시설을 한눈에 확인하세요.")
    
    # 다중 필터
    cols = st.columns(6)
    filters = {
        "화장실": cols[0].checkbox("화장실"),
        "편의점": cols[1].checkbox("편의점"),
        "카페/식당": cols[2].checkbox("맛집"),
        "흡연": cols[3].checkbox("흡연장"),
        "자판기": cols[4].checkbox("자판기"),
        "음수대": cols[5].checkbox("음수대")
    }

    # 지도 생성
    m = folium.Map(location=st.session_state['map_center'], zoom_start=st.session_state['map_zoom'])
    
    # 1. 공연장 마커 (항상 표시)
    venue_loc = VENUE_LOCATIONS.get("올림픽공원")
    for k, v in VENUE_LOCATIONS.items():
        if k in sel_concert['place']: venue_loc = v
    folium.Marker(
        venue_loc, 
        popup=folium.Popup(f"<b>{sel_concert['place']}</b><br>공연장", min_width=200, max_width=300),
        icon=folium.Icon(color='red', icon='star')
    ).add_to(m)

    # 2. 하이라이트 (검색 결과)
    if st.session_state['highlight_marker']:
        hm = st.session_state['highlight_marker']
        folium.Marker(
            hm['loc'], 
            popup=folium.Popup(hm['popup'], min_width=200, max_width=300),
            icon=folium.Icon(color=hm.get('color', 'blue'), icon='info-sign')
        ).add_to(m)

    # 3. 필터 마커
    for key, checked in filters.items():
        if checked:
            if key == "카페/식당":
                for _, row in df_rest.iterrows():
                    folium.Marker([row['lat'], row['lon']], 
                                popup=folium.Popup(f"<b>{row['name']}</b><br>{row['desc']}", min_width=200, max_width=300),
                                icon=folium.Icon(color='green', icon='cutlery')).add_to(m)
            else:
                subset = df_fac[df_fac['구분'].str.contains(key)]
                for _, row in subset.iterrows():
                    name = f"{row['구분']}" + (f" ({row['상세위치']})" if row['상세위치'] else "")
                    folium.Marker([row['위도'], row['경도']], 
                                popup=folium.Popup(name, min_width=200, max_width=300),
                                icon=folium.Icon(color='blue', icon='cloud')).add_to(m)

    st_folium(m, width=1400, height=600, key="main_map")
    
    # [NEW] 주차 정보 (실용성 어필)
    with st.expander("🚗 주차 및 교통 정보 보기", expanded=True):
        st.markdown("""
        - **가까운 주차장:** P5 (KSPO DOME 맞은편), P6 (SK핸드볼경기장 뒤)
        - **주차 요금:** 소형 10분당 600원 / 대형 10분당 1,200원 (공연 관람객 할인 없음)
        - **지하철:** 5호선/9호선 올림픽공원역 3번, 4번 출구
        """)

# --- TAB 4: 데이터 분석 ---
with tab4:
    st.markdown("### 📊 빅데이터로 본 혼잡도 예측")
    col_a, col_b = st.columns(2)
    with col_a:
        st.success("🏢 **숙박/식당:** 공연 종료 후 1시간 동안은 식당가가 매우 혼잡합니다.")
        if not df_food.empty: 
            st.line_chart(df_food.set_index('구분')[['한식당', '커피숍']])
    with col_b:
        st.info("🌏 **방문객:** 최근 외국인 관람객 비율이 증가 추세입니다.")
        if not df_users.empty: 
            st.bar_chart(df_users.set_index('구분')[['일반내국인', '일반외국인']])

# --- TAB 5: 팬 존 (NEW - 독창성/발전가능성) ---
with tab5:
    st.header("📢 Fan Zone")
    st.markdown("공연을 기다리며 응원의 메시지를 남겨보세요!")
    
    # 간단한 방명록 (Session State 활용)
    with st.form("fan_form", clear_on_submit=True):
        msg = st.text_input("메시지 입력")
        submitted = st.form_submit_button("응원하기 🚀")
        if submitted and msg:
            st.session_state['fan_messages'].insert(0, msg) # 최신글이 위로
            st.toast("메시지가 등록되었습니다!")
    
    for m in st.session_state['fan_messages']:
        st.write(f"💬 {m}")

# Footer
st.markdown("---")
st.caption("© 2025 OlyMate Team | 국민체육진흥공단 공공데이터 활용 | Developed by Streamlit")