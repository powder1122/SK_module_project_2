# pages/Quiz_Game.py
import streamlit as st
import random
import os
import time
from core.db_manager import DBManager

# --- 상수 정의 ---
TIME_LIMIT_SECONDS = 30
NUM_QUESTIONS = 10 # 출제할 문제 수

# --- [수정됨] DB 연결 및 문제 로딩 로직 분리 ---

# 1. DB 연결 (앱 세션에서 한 번만 실행)
if 'db' not in st.session_state:
    try:
        DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'quiz_questions.db')
        st.session_state.db = DBManager(DB_PATH)
    except Exception as e:
        st.error(f"데이터베이스 연결 중 오류가 발생했습니다: {e}")
        st.stop()

# 2. 문제 로딩 (DB 연결 후 앱 세션에서 한 번만 실행)
if 'all_questions' not in st.session_state:
    all_questions = st.session_state.db.get_all_questions()
    if not all_questions:
        st.error("데이터베이스에서 퀴즈 문제를 불러오는 데 실패했습니다. DB 파일과 내용을 확인해주세요.")
        st.stop()
    st.session_state.all_questions = all_questions

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

# --- 1. 게임 시작 화면 ---
if not st.session_state.get('game_started', False):
    st.title("피싱 제로 🎮")
    st.write(f"총 {NUM_QUESTIONS}개의 피싱 이메일 퀴즈를 통해 당신의 보안 지식을 테스트해보세요!")
    st.write(f"각 문제당 제한 시간은 **{TIME_LIMIT_SECONDS}초**입니다. 시간이 초과되면 오답으로 처리됩니다.")
    
    if st.button("게임 시작", type="primary"):
        initialize_game()

# --- 2. 게임 진행 화면 ---
elif not st.session_state.get('game_finished', False):
    current_question = st.session_state.questions[st.session_state.current_question_index]
    
    st.title(f"문제 {st.session_state.current_question_index + 1} / {len(st.session_state.questions)}")
    st.progress((st.session_state.current_question_index + 1) / len(st.session_state.questions))
    st.write(f"**현재 점수: {st.session_state.score}점**")

    st.subheader("📧 다음 이메일이 피싱인지 분석해보세요.")
    st.info(f"**제목:** {current_question['subject']}")
    st.text_area("이메일 내용", current_question['body'], height=200, disabled=True)

    # --- 2-1. 답변 제출 전 (타이머 작동) ---
    if not st.session_state.get('answer_submitted', False):
        timer_placeholder = st.empty()
        
        user_choice = st.radio(
            "이 이메일은 피싱일까요?", ('피싱', '정상'), index=None,
            key=f"question_{st.session_state.current_question_index}"
        )
        st.session_state.user_choice = user_choice

        submit_button = st.button("답변 제출")

        elapsed_time = time.time() - st.session_state.question_start_time
        remaining_time = max(0, TIME_LIMIT_SECONDS - int(elapsed_time))
        
        timer_placeholder.progress(remaining_time / TIME_LIMIT_SECONDS)
        st.markdown(f"남은 시간: **{remaining_time}초**")

        if submit_button or remaining_time == 0:
            if st.session_state.user_choice is None:
                if remaining_time == 0:
                    st.warning("시간 초과! 오답으로 처리됩니다.")
                    st.session_state.user_choice = "시간 초과"
                else:
                    st.warning("정답을 선택해주세요!")
                    st.stop()

            correct_answer = '피싱' if current_question['label'] == 1 else '정상'
            is_correct = (st.session_state.user_choice == correct_answer)

            if is_correct:
                st.session_state.score += 10

            st.session_state.user_answers.append({
                'question_data': current_question,
                'user_choice': st.session_state.user_choice,
                'is_correct': is_correct
            })
            
            st.session_state.answer_submitted = True
            st.rerun()
        
        time.sleep(0.1)
        st.rerun()

    # --- 2-2. 답변 제출 후 (해설 표시) ---
    else:
        last_answer = st.session_state.user_answers[-1]
        is_correct = last_answer['is_correct']
        user_choice = last_answer['user_choice']
        
        if user_choice == "시간 초과":
             st.error("⏳ 시간이 초과되어 오답 처리되었습니다.")
        elif is_correct:
            st.success("🎉 정답입니다!")
        else:
            st.error("😭 아쉽지만 오답입니다.")
        
        explanation_text = ""
        if current_question['label'] == 0:
            explanation_text = "정상 메일입니다!"
        else:
            explanation_text = current_question.get('explain') or "피싱 이메일의 특징을 주의 깊게 살펴보세요."

        st.info(f"**📖 해설**\n\n{explanation_text}")

        is_last_question = (st.session_state.current_question_index + 1) == len(st.session_state.questions)
        button_label = "결과 보기" if is_last_question else "다음 문제"

        if st.button(button_label, type="primary"):
            if not is_last_question:
                st.session_state.current_question_index += 1
                reset_question_state()
            else:
                st.session_state.game_finished = True
            st.rerun()

# --- 3. 게임 종료 화면 ---
else:
    st.title("게임 종료! 🥳")
    st.balloons()
    
    st.metric(label="최종 점수", value=f"{st.session_state.score} 점", delta=f"{st.session_state.score - 50} 점 (평균 50점 기준)")

    st.subheader("나의 답변 되돌아보기")
    for i, result in enumerate(st.session_state.user_answers):
        with st.expander(f"문제 {i+1}: { '✅ 정답' if result['is_correct'] else '❌ 오답' }"):
            q_data = result['question_data']
            st.write(f"**이메일 제목:** {q_data['subject']}")
            st.write(f"**나의 선택:** {result['user_choice']}")
            correct_answer_text = '피싱' if q_data['label'] == 1 else '정상'
            st.write(f"**정답:** {correct_answer_text}")

            explanation_text = ""
            if q_data['label'] == 0:
                explanation_text = "정상 메일입니다!"
            else:
                explanation_text = q_data.get('explain') or "피싱 이메일의 특징을 주의 깊게 살펴보세요."
            st.info(f"**해설:** {explanation_text}")

    if st.button("다시 시작하기"):
        initialize_game()