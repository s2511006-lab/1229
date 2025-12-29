import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 디자인
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="서초구 의류수거함 에코맵",
    page_icon="♻️",
    layout="wide"
)

# 스타일링 (CSS)
st.markdown("""
    <style>
    .main_title {
        font-size: 40px;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 10px;
    }
    .sub_text {
        font-size: 18px;
        color: #555;
        text-align: center;
        margin-bottom: 30px;
    }
    .highlight {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2E8B57;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터 로드 함수 (인코딩 에러 해결 버전)
# -----------------------------------------------------------------------------
# 파일을 안전하게 읽어오는 함수
def load_data_safe(file_source):
    # 1. utf-8로 먼저 시도 (대부분의 표준 파일)
    try:
        df = pd.read_csv(file_source, encoding='utf-8')
        return df
    except UnicodeDecodeError:
        pass # 실패하면 다음 단계로
    
    # 2. cp949로 시도 (한국 공공데이터 표준)
    try:
        df = pd.read_csv(file_source, encoding='cp949')
        return df
    except UnicodeDecodeError:
        pass

    # 3. euc-kr로 시도 (오래된 시스템)
    try:
        df = pd.read_csv(file_source, encoding='euc-kr')
        return df
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다. 인코딩 형식을 확인해주세요. 에러: {e}")
        return None

# 전처리 함수
def preprocess_data(df):
    if df is None:
        return None
        
    # 필요한 컬럼만 추출 (데이터 파일의 실제 컬럼명 기준)
    # 업로드해주신 파일 컬럼: '설치장소명', '소재지도로명주소', '위도', '경도', '상세위치' 등
    required_cols = ['설치장소명', '소재지도로명주소', '위도', '경도']
    
    # 데이터에 '상세위치'가 있다면 포함, 없으면 제외
    if '상세위치' in df.columns:
        required_cols.append('상세위치')
        
    # 필수 컬럼이 있는지 확인
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 다음 필수 항목이 없습니다: {missing_cols}")
        return None

    # 결측치 제거 (위도, 경도가 없는 데이터는 지도에 못 찍으므로 제외)
    df = df.dropna(subset=['위도', '경도'])
    return df

# -----------------------------------------------------------------------------
# 3. 메인 UI 구성
# -----------------------------------------------------------------------------

# 헤더 섹션
st.markdown('<div class="main_title">♻️ 서초구 의류수거함 에코맵</div>', unsafe_allow_html=True)
st.markdown("""
<div class="sub_text">
    패스트패션으로 인해 버려지는 옷들이 환경을 아프게 하고 있습니다.<br>
    가까운 의류수거함을 찾아 소중한 자원을 재활용해주세요.
</div>
""", unsafe_allow_html=True)

# 사이드바: 문제 정의 및 사용법
with st.sidebar:
    st.header("🌍 왜 이 앱이 필요한가요?")
    st.info("""
    **문제점:**
    유행에 따라 옷을 쉽게 사고 쉽게 버리는 '패스트패션' 트렌드로 인해 의류 폐기물이 급증하고 있습니다.
    
    **우리의 목표:**
    서초구 주민들이 가장 가까운 수거함을 쉽게 찾아 의류 재활용률을 높이는 것입니다.
    """)
    st.divider()
    st.write("**데이터 출처:** 서초구청")

# -----------------------------------------------------------------------------
# 4. 데이터 로딩 실행
# -----------------------------------------------------------------------------
# 기본 파일명 (GitHub에 업로드한 파일명과 똑같아야 합니다!)
default_csv_file = "________________20250218.csv"

# 파일 업로더 제공 (혹시 다른 파일을 쓰고 싶을 때를 대비)
uploaded_file = st.file_uploader("CSV 파일 업로드 (기본 파일이 없다면 업로드해주세요)", type=['csv'])

if uploaded_file is not None:
    # 사용자가 직접 업로드한 경우
    raw_df = load_data_safe(uploaded_file)
else:
    # GitHub에 올려둔 기본 파일 사용 시도
    try:
        raw_df = load_data_safe(default_csv_file)
    except FileNotFoundError:
        st.error(f"기본 데이터 파일({default_csv_file})을 찾을 수 없습니다. GitHub에 파일을 올렸는지 확인하거나, 위에서 파일을 직접 업로드해주세요.")
        st.stop()

# 전처리
df = preprocess_data(raw_df)

if df is None:
    st.stop() # 데이터가 없으면 여기서 중단

# -----------------------------------------------------------------------------
# 5. 내 위치 설정 및 거리 계산 로직
# -----------------------------------------------------------------------------

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 📍 내 위치 설정")
    st.write("현재 위치와 가장 가까운 랜드마크를 선택하세요.")
    
    # 서초구 주요 거점 좌표
    landmarks = {
        "서초구청 (기본)": (37.483574, 127.032692),
        "강남역": (37.498095, 127.027610),
        "교대역": (37.493968, 127.014658),
        "고속터미널": (37.504914, 127.004915),
        "양재역": (37.484147, 127.034631),
        "방배역": (37.481533, 126.997637)
    }
    
    selected_landmark = st.selectbox("주변 랜드마크 선택", list(landmarks.keys()))
    user_location = landmarks[selected_landmark]
    
    st.info(f"선택된 위치: **{selected_landmark}**")
    
    # 거리 계산 함수
    def calculate_distance(row):
        bin_loc = (row['위도'], row['경도'])
        return geodesic(user_location, bin_loc).meters

    # 거리 계산 적용
    df['거리(m)'] = df.apply(calculate_distance, axis=1)
    
    # 가장 가까운 수거함 5개 추출 (거리순 정렬)
    nearest_bins = df.sort_values(by='거리(m)').head(5)
    
    st.markdown("### 🏃 가장 가까운 수거함 TOP 5")
    for idx, row in nearest_bins.iterrows():
        # 상세위치가 있으면 표시, 없으면 '정보없음'
        detail_loc = row['상세위치'] if '상세위치' in row else "상세정보 없음"
        
        with st.expander(f"📍 {row['설치장소명']} ({int(row['거리(m)'])}m)"):
            st.write(f"**주소:** {row['소재지도로명주소']}")
            st.write(f"**상세위치:** {detail_loc}")

with col2:
    st.markdown("### 🗺️ 의류수거함 지도")
    
    # 지도 생성 (사용자 위치 중심)
    m = folium.Map(location=user_location, zoom_start=15)
    
    # 1. 사용자 위치 마커 (빨간색)
    folium.Marker(
        user_location,
        popup="내 위치",
        tooltip="내 위치",
        icon=folium.Icon(color='red', icon='user')
    ).add_to(m)
    
    # 2. 가장 가까운 5개 수거함 마커 (초록색)
    for idx, row in nearest_bins.iterrows():
        folium.Marker(
            [row['위도'], row['경도']],
            popup=f"<b>{row['설치장소명']}</b><br>{int(row['거리(m)'])}m",
            tooltip=f"{row['설치장소명']} ({int(row['거리(m)'])}m)",
            icon=folium.Icon(color='green', icon='recycle', prefix='fa')
        ).add_to(m)

    # 지도를 스트림릿에 표시
    st_folium(m, width="100%", height=600)

# -----------------------------------------------------------------------------
# 6. 푸터
# -----------------------------------------------------------------------------
st.divider()
st.markdown("""
    <div style="text-align: center; color: #888;">
        <p>작은 실천이 모여 깨끗한 지구를 만듭니다. 오늘 안 입는 옷을 정리해보는 건 어떨까요?</p>
    </div>
""", unsafe_allow_html=True)
