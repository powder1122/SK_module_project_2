# main_app.py 
# 메인
import streamlit as st

st.set_page_config(
    page_title="피싱 제로",
    page_icon="🛡️",
)

st.title("피싱 제로에 오신 것을 환영합니다! 🛡️")
st.write("당신의 사이버 보안 의식을 테스트하고, 피싱 공격에 대처하는 방법을 배워보세요.")
st.write("---")
st.write("왼쪽 사이드바에서 '🎮 퀴즈 게임'을 선택하여 게임을 시작할 수 있습니다.")

# 게임에 필요한 데이터가 없다면, 초기화 스크립트를 실행하도록 유도
st.info("게임을 시작하기 전에, 문제 데이터베이스를 준비해주세요.")