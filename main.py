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
    .bin-card {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = "________________20250218.csv"  # 실제 파일 경로에 맞게 수정해주세요
    
    # 인코딩 처리
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
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

df = load_data()

# -----------------------------------------------------------------------------
# 3. 메인 UI
# -----------------------------------------------------------------------------
st.markdown('<div class="main_title">♻️ 서초구 의류수거함 에코맵</div>', unsafe_allow_html=True)
st.markdown('<div class="sub_text">현재 위치를 파악하여 가장 가까운 수거함과 <b>실제 거리 모습(로드뷰)</b>을 보여드립니다.</div>', unsafe_allow_html=True)

# 3-1. 위치 정보 가져오기
loc = get_geolocation()

col1, col2 = st.columns([1.2, 2]) # 왼쪽 영역을 조금 더 넓힘

with col1:
    st.markdown("### 📍 내 위치 & 주변 수거함")
    
    # 위치 처리 로직
    user_location = (37.483574, 127.032692) # 기본값 (서초구청)
    
    if loc:
        user_location = (loc['coords']['latitude'], loc['coords']['longitude'])
        st.success("✅ 현재 위치를 찾았습니다!")
    else:
        st.info("📡 위치 확인 중... (허용해주세요)")
        st.caption("위치를 못 찾으면 '서초구청' 기준으로 안내합니다.")

    # -------------------------------------------------------------------------
    # 4. 거리 계산 및 로드뷰 링크 생성
    # -------------------------------------------------------------------------
    if df is not None:
        def calculate_distance(row):
            bin_loc = (row['위도'], row['경도'])
            return geodesic(user_location, bin_loc).meters

        df['거리(m)'] = df.apply(calculate_distance, axis=1)
        nearest_bins = df.sort_values(by='거리(m)').head(5)

        st.markdown("---")
        st.subheader(f"🏃 가장 가까운 수거함 TOP 5")
        
        # 리스트 출력
        for idx, row in nearest_bins.iterrows():
            dist = int(row['거리(m)'])
            detail = row['상세위치'] if '상세위치' in row else "상세 정보 없음"
            
            # 카카오맵 로드뷰 URL 생성
            roadview_url = f"https://map.kakao.com/link/roadview/{row['위도']},{row['경도']}"
            
            with st.container():
                st.markdown(f"""
                <div class="bin-card">
                    <h4>📍 {row['설치장소명']} <span style="color:#2E8B57; font-size:0.8em;">({dist}m)</span></h4>
                    <p><b>주소:</b> {row['소재지도로명주소']}<br>
                    <b>위치:</b> {detail}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 로드뷰 버튼
                st.link_button(f"📸 {row['설치장소명']} 로드뷰 보기", roadview_url)

    else:
        st.error("데이터 파일을 찾을 수 없습니다.")

with col2:
    st.markdown("### 🗺️ 지도 확인")
    
    if df is not None:
        m = folium.Map(location=user_location, zoom_start=15)

        # 내 위치
        folium.Marker(
            user_location,
            popup="내 위치",
            icon=folium.Icon(color='red', icon='user')
        ).add_to(m)

        # 수거함 마커
        for idx, row in nearest_bins.iterrows():
            folium.Marker(
                [row['위도'], row['경도']],
                popup=f"<b>{row['설치장소명']}</b><br>{int(row['거리(m)'])}m",
                tooltip=row['설치장소명'],
                icon=folium.Icon(color='green', icon='recycle', prefix='fa')
            ).add_to(m)

        st_folium(m, width="100%", height=600)
    
    # [수정] 요청하신 하단 설명 문구와 이미지는 모두 삭제되었습니다.

# 푸터
st.divider()
st.caption("※ 로드뷰는 카카오맵 서비스로 연결됩니다.")
