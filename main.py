import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 디자인
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="서초구 의류수거함 에코맵",
    page_icon="♻️",
    layout="wide"
)

st.markdown("""
    <style>
    .main_title { font-size: 40px; fontWeight: bold; color: #2E8B57; text-align: center; margin-bottom: 10px; }
    .sub_text { font-size: 18px; color: #555; text-align: center; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 기본 파일명 (GitHub 파일명)
    file_path = "________________20250218.csv"
    
    # 1. utf-8 시도
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        # 2. cp949 시도
        try:
            df = pd.read_csv(file_path, encoding='cp949')
        except:
            return None
            
    # 전처리
    required_cols = ['설치장소명', '소재지도로명주소', '위도', '경도']
    if '상세위치' in df.columns:
        required_cols.append('상세위치')
        
    df = df[required_cols].dropna(subset=['위도', '경도'])
    return df

# 데이터 불러오기
df = load_data()

# -----------------------------------------------------------------------------
# 3. 메인 UI 및 자동 위치 파악
# -----------------------------------------------------------------------------
st.markdown('<div class="main_title">♻️ 서초구 의류수거함 에코맵</div>', unsafe_allow_html=True)
st.markdown('<div class="sub_text">현재 위치를 자동으로 파악하여 가장 가까운 수거함을 안내합니다.</div>', unsafe_allow_html=True)

# 3-1. 위치 정보 가져오기 (핵심 기능)
# 브라우저에서 위치 권한 요청이 뜨면 '허용'을 눌러야 합니다.
loc = get_geolocation()

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 📍 내 위치 정보")
    
    # 기본 위치 (서초구청) - 위치 권한 거부시 사용
    user_location = (37.483574, 127.032692)
    location_status = "기본 위치 (서초구청)"

    # 위치 정보가 들어왔다면 덮어쓰기
    if loc:
        user_location = (loc['coords']['latitude'], loc['coords']['longitude'])
        location_status = "✅ 현재 위치 파악 완료!"
        st.success(location_status)
    else:
        st.info("📡 위치를 찾는 중입니다... (브라우저 권한 허용 필요)")
        st.caption("위치를 못 찾으면 서초구청을 기준으로 안내합니다.")

    # -------------------------------------------------------------------------
    # 4. 거리 계산 및 결과 출력
    # -------------------------------------------------------------------------
    if df is not None:
        # 거리 계산 함수
        def calculate_distance(row):
            bin_loc = (row['위도'], row['경도'])
            return geodesic(user_location, bin_loc).meters

        df['거리(m)'] = df.apply(calculate_distance, axis=1)
        nearest_bins = df.sort_values(by='거리(m)').head(5)

        st.markdown("### 🏃 가장 가까운 수거함 TOP 5")
        for idx, row in nearest_bins.iterrows():
            detail = row['상세위치'] if '상세위치' in row else ""
            with st.expander(f"📍 {row['설치장소명']} ({int(row['거리(m)'])}m)"):
                st.write(f"주소: {row['소재지도로명주소']}")
                st.write(f"상세: {detail}")
    else:
        st.error("데이터 파일을 찾을 수 없습니다.")

with col2:
    st.markdown("### 🗺️ 지도 확인")
    
    if df is not None:
        # 지도 생성
        m = folium.Map(location=user_location, zoom_start=15)

        # 내 위치 마커 (빨간색)
        folium.Marker(
            user_location,
            popup="내 위치",
            icon=folium.Icon(color='red', icon='user')
        ).add_to(m)

        # 수거함 마커 (초록색)
        for idx, row in nearest_bins.iterrows():
            folium.Marker(
                [row['위도'], row['경도']],
                popup=f"<b>{row['설치장소명']}</b><br>{int(row['거리(m)'])}m",
                tooltip=row['설치장소명'],
                icon=folium.Icon(color='green', icon='recycle', prefix='fa')
            ).add_to(m)

        st_folium(m, width="100%", height=600)

# 푸터
st.divider()
st.caption("※ 위치 정보는 브라우저를 통해 실시간으로 파악되며 서버에 저장되지 않습니다.")
