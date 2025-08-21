import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="피싱 제로 - 보안 교육 플랫폼",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 추가
st.markdown("""
<style>
    /* 전체 앱 배경 및 폰트 색상 */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Streamlit의 기본 흰색 배경을 가진 요소들을 투명하게 처리 */
    [data-testid="stAppViewContainer"] > .main {
        background-color: transparent;
    }
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    [data-testid="stToolbar"] {
        background-color: transparent;
    }

    /* 메인 페이지 타이틀 */
    .main-title {
        font-size: 4em; 
        text-align: center; 
        font-weight: bold;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.5);
        margin-bottom: 1rem;
    }
    .main-subtitle {
        text-align: center; 
        font-size: 1.5em; 
        opacity: 0.9; 
        margin-bottom: 2rem;
    }

    /* 카드 스타일 */
    .feature-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        border: 2px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
        text-align: center;
    }
    
    .feature-card:hover {
        background: rgba(255, 255, 255, 0.15);
        transform: translateY(-5px);
        border-color: rgba(255, 255, 255, 0.4);
    }
    
    .feature-icon {
        font-size: 3em;
        margin-bottom: 1rem;
    }
    
    .feature-title {
        font-size: 1.5em;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        background: rgba(255, 255, 255, 0.1);
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 15px;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.5);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-title">🛡️ 피싱 제로</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">피싱 사기로부터 안전한 디지털 세상을 만들어가요</div>', unsafe_allow_html=True)
    
    # 기능 소개 섹션
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">퀴즈 게임</div>
            <p>실제 피싱 사례를 기반으로 한 인터랙티브 퀴즈를 통해 피싱 메일을 식별하는 능력을 기르세요. 다양한 난이도의 문제로 단계별 학습이 가능합니다.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <style>
        .big-btn button {
            font-size: 1.3em !important;
            padding: 1em 2em !important;
            border-radius: 20px !important;
            margin-top: 1em;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("퀴즈 게임 바로가기", key="quiz_game_card_btn", use_container_width=True):
            st.switch_page("pages/quiz_game.py")
        st.markdown('<div class="big-btn"></div>', unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📧</div>
            <div class="feature-title">메일 분석</div>
            <p>의심스러운 이메일(.eml) 파일을 업로드하면 AI가 헤더, 본문, 첨부파일, URL 등을 종합적으로 분석하여 피싱 위험도를 평가해드립니다.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <style>
        .big-btn2 button {
            font-size: 1.3em !important;
            padding: 1em 2em !important;
            border-radius: 20px !important;
            margin-top: 1em;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("메일 분석 바로가기", key="mail_analysis_card_btn", use_container_width=True):
            st.switch_page("pages/mail_analysis.py")
        st.markdown('<div class="big-btn2"></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 사용 방법 안내
    st.markdown("### 📋 사용 방법")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **1️⃣ 페이지 선택**  
        왼쪽 사이드바에서 원하는 기능을 선택하세요.
        """)
    with col2:
        st.markdown("""
        **2️⃣ 기능 사용**  
        각 페이지에서 제공하는 기능을 체험해보세요.
        """)
    with col3:
        st.markdown("""
        **3️⃣ 학습 완료**  
        피싱 방어 능력을 향상시키고 안전한 디지털 생활을 유지하세요.
        """)
    
    # 보안 팁
    with st.expander("💡 피싱 방어 핵심 팁"):
        st.markdown("""
        - **발신자 확인**: 이메일 주소와 발신자 정보를 꼼꼼히 확인하세요
        - **링크 주의**: 의심스러운 링크는 클릭하지 말고, URL을 마우스로 호버해서 확인하세요
        - **개인정보 보호**: 이메일을 통해 비밀번호나 개인정보를 요구하는 경우 의심하세요
        - **첨부파일 검증**: 예상치 못한 첨부파일은 열기 전에 발신자에게 확인하세요
        - **2차 인증**: 중요한 계정에는 2단계 인증을 설정하세요
        """)

if __name__ == "__main__":
    main()