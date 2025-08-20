# API 사용
import streamlit as st
import google.generativeai as genai


# st.secrets를 통해 API 키를 안전하게 불러옵니다.
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    st.error("Gemini API 키를 설정하는 중 오류가 발생했습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    # API 키가 설정되어 있지 않으면 오류 메시지를 표시합니다.
    if not st.secrets.get("GOOGLE_API_KEY"):
        st.error("Gemini API 키가 설정되어 있지 않습니다. .streamlit/secrets.toml 파일에 GOOGLE_API_KEY를 추가해주세요.")

def get_gemini_explanation(subject: str, body: str, label: int) -> str:
    """
    주어진 이메일의 정답 레이블에 따라 해설을 생성합니다.
    - 피싱 메일(label=1)인 경우: Gemini API를 호출하여 상세한 이유를 분석합니다.
    - 정상 메일(label=0)인 경우: 안전하다는 간단한 메시지를 반환합니다.
    """
    # label이 0 (정상 메일)인 경우, API 호출 없이 간단한 메시지를 반환합니다.
    if label == 0:
        return "특별한 위협 요소가 발견되지 않은 **정상 메일**입니다. ✅"

    # label이 1 (피싱 메일)인 경우에만 API를 호출합니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 피싱 이메일 분석에 더 초점을 맞춘 프롬프트
    prompt = f"""
    당신은 뛰어난 사이버 보안 전문가입니다.
    아래 주어진 이메일은 **피싱 이메일**로 이미 판명되었습니다.
    당신의 임무는 이 이메일이 왜 피싱 이메일인지에 대한 결정적인 단서들을 찾아내어, IT 비전문가도 쉽게 이해할 수 있도록 설명하는 것입니다.

    다음 항목들을 중심으로 분석하고, 해당하는 단서를 이메일 본문에서 찾아 **볼드체**로 강조하며 설명해주세요.
    - **긴급성 또는 위협적인 어조**: 사용자를 압박하여 성급한 판단을 유도하는 표현
    - **의심스러운 링크 또는 첨부파일**: 공식적이지 않은 URL 주소, 단축 URL, 위험한 파일 형식 등
    - **일반적인 인사말**: '고객님'과 같이 불특정 다수를 대상으로 한 인사
    - **개인정보 요구**: 비밀번호, 금융 정보 등 민감한 정보 입력을 직접적으로 요구
    - **어색한 문법 또는 오탈자**: 프로페셔널하지 않은 이메일의 특징

    --- 이메일 정보 ---
    - 제목: {subject}
    - 본문: {body}
    ---
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"해설을 생성하는 중 오류가 발생했습니다: {e}"









