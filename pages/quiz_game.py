import streamlit as st
import random
import time
import requests

# 페이지 설정
st.set_page_config(
    page_title="퀴즈 게임 - 피싱 제로",
    page_icon="🎯",
    layout="wide"
)

# --- 상수 정의 ---
TIME_LIMIT_SECONDS = 30
NUM_QUESTIONS = 10
FASTAPI_URL = "http://localhost:8000"  # FastAPI 서버 주소

# CSS 스타일 추가 (메일 분석 페이지와 일관성 유지)
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    [data-testid="stAppViewContainer"] > .main {
        background-color: transparent;
    }
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    
    /* 게임 카드 스타일 */
    .game-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        border: 2px solid rgba(255, 255, 255, 0.2);
    }
    
    /* 점수 표시 */
    .score-display {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 1rem;
        text-align: center;
        font-size: 1.2em;
        font-weight: bold;
    }
    
    /* 타이머 스타일 */
    .timer-warning {
        color: #ff4444 !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 문제 로딩 로직 변경 (API 호출 대신 로컬 데이터 사용) ---
def load_questions_from_local():
    """로컬에서 샘플 퀴즈 문제를 불러오는 함수 (API 서버가 없을 경우 대비)"""
    sample_questions = [
        {
            "id": 1,
            "subject": "귀하의 계정이 보안 위험에 노출되었습니다!",
            "body": "안녕하세요,\n\n저희 보안팀에서 귀하의 계정에 비정상적인 접근을 감지했습니다. 즉시 아래 링크를 클릭하여 계정을 보호하세요.\n\n[긴급 보안 업데이트] https://secure-bank-update.com/verify\n\n24시간 이내에 조치하지 않으면 계정이 영구적으로 잠길 수 있습니다.\n\n감사합니다.\n보안팀",
            "label": 1  # 피싱
        },
        {
            "id": 2,
            "subject": "회의 자료 공유",
            "body": "안녕하세요 김대리님,\n\n오늘 회의에서 논의된 프로젝트 자료를 첨부파일로 보내드립니다. 검토 후 피드백 부탁드려요.\n\n첨부: 프로젝트_계획서_v2.pdf\n\n감사합니다.\n박과장",
            "label": 0  # 정상
        },
        {
            "id": 3,
            "subject": "축하합니다! 1억원 당첨!",
            "body": "축하합니다!\n\n귀하께서 온라인 추첨에 당첨되어 1억원의 상금을 받게 되셨습니다!\n\n상금을 수령하시려면 아래 정보를 회신해주세요:\n- 성명\n- 주민등록번호\n- 계좌번호\n\n빠른 처리를 위해 24시간 내 회신 바랍니다.",
            "label": 1  # 피싱
        }
    ]
    return sample_questions

def load_questions_from_api():
    """FastAPI API에서 퀴즈 문제를 불러오는 함수"""
    try:
        response = requests.get(f"{FASTAPI_URL}/questions", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        st.warning("API 서버에 연결할 수 없어 샘플 문제를 사용합니다.")
        return load_questions_from_local()

# 1. 문제 로딩 (앱 세션에서 한 번만 실행)
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = load_questions_from_api()

# --- 게임 상태 변수 초기화 함수 ---
def initialize_game():
    """게임을 시작하거나 재시작할 때 상태를 초기화하는 함수"""
    random.shuffle(st.session_state.all_questions)
    st.session_state.questions = st.session_state.all_questions[:NUM_QUESTIONS]
    
    st.session_state.game_started = True
    st.session_state.game_finished = False
    st.session_state.current_question_index = 0
    st.session_state.score = 0
    st.session_state.user_answers = []
    reset_question_state()
    st.rerun()

def reset_question_state():
    """다음 문제로 넘어갈 때 문제 관련 상태를 초기화하는 함수"""
    st.session_state.answer_submitted = False
    st.session_state.question_start_time = time.time()
    st.session_state.user_choice = None

def submit_answer_to_api(question_id, user_choice):
    """FastAPI에 답변 제출 (API 서버가 없을 경우 로컬 처리)"""
    try:
        payload = {
            "question_id": question_id,
            "user_choice": user_choice
        }
        response = requests.post(f"{FASTAPI_URL}/submit_answer", json=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        # API 서버가 없을 경우 로컬에서 처리
        current_question = next(q for q in st.session_state.questions if q['id'] == question_id)
        is_phishing = current_question['label'] == 1
        correct_answer = '피싱' if is_phishing else '정상'
        is_correct = user_choice == correct_answer
        
        return {
            'is_correct': is_correct,
            'explanation': f"이 메일은 {correct_answer} 메일입니다. " + 
                          ("피싱 메일의 특징을 잘 파악하셨네요!" if is_correct 
                           else "다시 한번 주의깊게 살펴보세요."),
            'score_earned': 10 if is_correct else 0
        }

# --- 1. 게임 시작 화면 ---
if not st.session_state.get('game_started', False):
    st.markdown('<div style="text-align: center;"><h1>🎯 피싱 탐지 퀴즈</h1></div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="game-card">
        <h3>🎮 게임 규칙</h3>
        <ul>
            <li>총 <strong>{}</strong>개의 이메일을 분석합니다</li>
            <li>각 문제당 제한 시간은 <strong>{}초</strong>입니다</li>
            <li>시간이 초과되면 자동으로 오답 처리됩니다</li>
            <li>정답 시 10점을 획득합니다</li>
        </ul>
    </div>
    """.format(NUM_QUESTIONS, TIME_LIMIT_SECONDS), unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 게임 시작하기", type="primary", use_container_width=True):
            initialize_game()

# --- 2. 게임 진행 화면 ---
elif not st.session_state.get('game_finished', False):
    current_question = st.session_state.questions[st.session_state.current_question_index]
    
    # 진행률 및 점수 표시
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 문제 {st.session_state.current_question_index + 1} / {len(st.session_state.questions)}")
        progress = (st.session_state.current_question_index + 1) / len(st.session_state.questions)
        st.progress(progress)
    
    with col2:
        st.markdown(f'<div class="score-display">🏆 {st.session_state.score}점</div>', unsafe_allow_html=True)

    # 이메일 내용 표시
    st.markdown("### 📧 이메일 분석")
    with st.container():
        st.markdown(f"**제목:** {current_question['subject']}")
        st.text_area("이메일 본문", current_question['body'], height=200, disabled=True)

    # --- 2-1. 답변 제출 전 (타이머 작동) ---
    if not st.session_state.get('answer_submitted', False):
        elapsed_time = time.time() - st.session_state.question_start_time
        remaining_time = max(0, TIME_LIMIT_SECONDS - int(elapsed_time))
        
        # 타이머 표시
        timer_col1, timer_col2 = st.columns([3, 1])
        with timer_col1:
            st.progress(remaining_time / TIME_LIMIT_SECONDS)
        with timer_col2:
            if remaining_time <= 5:
                st.markdown(f'<div class="timer-warning">⏰ {remaining_time}초</div>', unsafe_allow_html=True)
            else:
                st.write(f"⏱️ {remaining_time}초")

        # 답변 선택
        user_choice = st.radio(
            "### 🤔 이 이메일은 피싱 메일일까요?", 
            ['피싱', '정상'], 
            index=None,
            key=f"question_{st.session_state.current_question_index}"
        )
        st.session_state.user_choice = user_choice

        # 제출 버튼
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_button = st.button("📝 답변 제출", type="primary", use_container_width=True)

        # 시간 초과 또는 답변 제출 처리
        if submit_button or remaining_time == 0:
            if st.session_state.user_choice is None:
                if remaining_time == 0:
                    st.warning("⏰ 시간 초과! 오답으로 처리됩니다.")
                    st.session_state.user_choice = "시간 초과"
                else:
                    st.warning("답변을 선택해주세요!")
                    st.stop()

            # 답변 처리
            if st.session_state.user_choice != "시간 초과":
                result = submit_answer_to_api(current_question['id'], st.session_state.user_choice)
                is_correct = result['is_correct']
                explanation_text = result['explanation']
                score_earned = result['score_earned']
            else:
                is_correct = False
                explanation_text = "시간 초과로 인해 오답 처리되었습니다."
                score_earned = 0

            if is_correct:
                st.session_state.score += score_earned

            st.session_state.user_answers.append({
                'question_data': current_question,
                'user_choice': st.session_state.user_choice,
                'is_correct': is_correct,
                'explanation': explanation_text
            })
            
            st.session_state.answer_submitted = True
            st.rerun()
        
        # 실시간 업데이트를 위한 재실행
        if remaining_time > 0:
            time.sleep(0.5)
            st.rerun()

    # --- 2-2. 답변 제출 후 (해설 표시) ---
    else:
        last_answer = st.session_state.user_answers[-1]
        is_correct = last_answer['is_correct']
        user_choice = last_answer['user_choice']
        explanation_text = last_answer['explanation']
        
        # 결과 표시
        if user_choice == "시간 초과":
            st.error("⏳ 시간이 초과되어 오답 처리되었습니다.")
        elif is_correct:
            st.success("🎉 정답입니다!")
        else:
            st.error("😔 아쉽지만 오답입니다.")
        
        # 해설 표시
        st.info(f"**💡 해설**\n\n{explanation_text}")

        # 다음 문제 또는 결과 보기
        is_last_question = (st.session_state.current_question_index + 1) == len(st.session_state.questions)
        button_label = "🏆 결과 보기" if is_last_question else "➡️ 다음 문제"

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(button_label, type="primary", use_container_width=True):
                if not is_last_question:
                    st.session_state.current_question_index += 1
                    reset_question_state()
                else:
                    st.session_state.game_finished = True
                st.rerun()

# --- 3. 게임 종료 화면 ---
else:
    st.markdown('<div style="text-align: center;"><h1>🏆 게임 완료!</h1></div>', unsafe_allow_html=True)
    st.balloons()
    
    # 최종 점수 표시
    total_possible = len(st.session_state.questions) * 10
    score_percentage = (st.session_state.score / total_possible) * 100
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div class="score-display" style="font-size: 2em; padding: 2rem;">
            최종 점수<br>
            <strong>{st.session_state.score} / {total_possible}점</strong><br>
            <span style="font-size: 0.7em;">({score_percentage:.1f}%)</span>
        </div>
        """, unsafe_allow_html=True)

    # 성과 평가
    if score_percentage >= 80:
        st.success("🌟 우수! 피싱 탐지 전문가 수준입니다!")
    elif score_percentage >= 60:
        st.info("👍 양호! 기본적인 피싱 탐지 능력을 갖추고 있습니다.")
    elif score_percentage >= 40:
        st.warning("⚠️ 보통! 더 많은 연습이 필요합니다.")
    else:
        st.error("🚨 주의! 피싱 메일에 대한 경각심을 높여야 합니다.")

    # 상세 결과 보기
    st.markdown("### 📊 상세 결과")
    correct_count = sum(1 for result in st.session_state.user_answers if result['is_correct'])
    
    for i, result in enumerate(st.session_state.user_answers):
        status_icon = "✅" if result['is_correct'] else "❌"
        with st.expander(f"문제 {i+1}: {status_icon} {'정답' if result['is_correct'] else '오답'}"):
            q_data = result['question_data']
            st.write(f"**이메일 제목:** {q_data['subject']}")
            st.write(f"**나의 답변:** {result['user_choice']}")
            
            correct_answer_text = '피싱' if q_data['label'] == 1 else '정상'
            st.write(f"**정답:** {correct_answer_text}")
            st.info(f"**해설:** {result['explanation']}")

    # 재시작 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 다시 도전하기", type="primary", use_container_width=True):
            # 게임 상태 초기화
            for key in ['game_started', 'game_finished', 'current_question_index', 
                       'score', 'user_answers', 'answer_submitted', 'user_choice']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()