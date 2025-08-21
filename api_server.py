# api_server.py

from fastapi import FastAPI, HTTPException
from core.db_manager import DBManager
from pydantic import BaseModel
import os
import uvicorn
import whois
from datetime import datetime
import requests
import time
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- 환경 변수에서 API 키 로드 ---
VT_API_KEY = os.getenv("VT_API_KEY")

class AnswerRequest(BaseModel):
    question_id: int
    user_choice: str

# --- DB 경로 설정 및 DBManager 인스턴스 생성 ---
# 이 파일의 위치를 기준으로 상대 경로를 계산합니다.
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'data', 'quiz_questions.db')
    db_manager = DBManager(DB_PATH)
except Exception as e:
    print(f"DBManager 초기화 실패: {e}")
    db_manager = None

# --- FastAPI 앱 초기화 ---
app = FastAPI()


# --- VirusTotal 설정 ---
VT_API_URL = "https://www.virustotal.com/api/v3"

# --- API 엔드포인트 ---
@app.get("/questions")
async def get_all_questions():
    """모든 퀴즈 문제를 불러오는 API"""
    if db_manager is None:
        raise HTTPException(status_code=500, detail="데이터베이스 연결에 실패했습니다.")
        
    questions = db_manager.get_all_questions()
    if not questions:
        raise HTTPException(status_code=404, detail="퀴즈 문제를 찾을 수 없습니다.")
    return questions

@app.post("/submit_answer")
async def submit_answer(answer_request: AnswerRequest):
    """퀴즈 답변을 제출하고 결과를 반환하는 API"""
    if db_manager is None:
        raise HTTPException(status_code=500, detail="데이터베이스 연결에 실패했습니다.")
    
    try:
        # 문제 정보 조회
        question = db_manager.get_question_by_id(answer_request.question_id)
        if not question:
            raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
        
        # 정답 확인
        is_phishing = question['label'] == 1
        correct_answer = '피싱' if is_phishing else '정상'
        is_correct = answer_request.user_choice == correct_answer
        
        # 점수 계산
        score_earned = 10 if is_correct else 0
        
        # 해설 생성 (데이터베이스의 explain 컬럼을 우선 사용)
        if question.get('explain'):
            # 데이터베이스에 해설이 있는 경우 사용
            base_explanation = question['explain']
            if is_correct:
                explanation = f"정답입니다! {base_explanation}"
            else:
                explanation = f"아쉽지만 오답입니다. {base_explanation}"
        else:
            # 데이터베이스에 해설이 없는 경우 기본 해설 사용
            if is_correct:
                if is_phishing:
                    explanation = "정답입니다! 이 메일은 피싱 메일입니다. 의심스러운 링크, 긴급성을 강조하는 문구, 개인정보 요구 등의 특징을 잘 파악하셨네요."
                else:
                    explanation = "정답입니다! 이 메일은 정상 메일입니다. 발신자가 명확하고, 내용이 자연스러우며, 의심스러운 요소가 없음을 잘 판단하셨습니다."
            else:
                if is_phishing:
                    explanation = "아쉽지만 오답입니다. 이 메일은 피싱 메일입니다. 의심스러운 링크, 개인정보 요구, 긴급성 강조 등의 피싱 특징을 다시 한번 확인해보세요."
                else:
                    explanation = "아쉽지만 오답입니다. 이 메일은 정상 메일입니다. 발신자의 신뢰성, 내용의 자연스러움, 요청사항의 합리성 등을 종합적으로 판단해보세요."
        
        return {
            'is_correct': is_correct,
            'explanation': explanation,
            'score_earned': score_earned,
            'correct_answer': correct_answer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/domain_info/{domain_name}")
async def get_domain_info(domain_name: str):
    """도메인 Whois 정보를 조회하는 API"""
    try:
        # www. 같은 접두사는 제거하고 조회
        if domain_name.lower().startswith('www.'):
            domain_name = domain_name[4:]
            
        domain_info = whois.whois(domain_name)

        # 도메인 등록 여부 확인
        if domain_info.status is None and domain_info.registrar is None:
             raise ValueError("등록되지 않았거나 조회할 수 없는 도메인입니다.")

        # 도메인 생성일자 추출 (피싱 탐지에 핵심)
        creation_date = domain_info.creation_date

        # creation_date가 리스트 형태일 수 있음
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        # 생성 후 경과 시간 계산
        days_since_creation = (datetime.now() - creation_date).days if creation_date else -1


        # 직렬화 가능한 형태로 변환
        return {
            "domain_name": domain_info.domain_name,
            "registrar": domain_info.registrar,
            "creation_date": creation_date.isoformat() if creation_date else None,
            "expiration_date": domain_info.expiration_date.isoformat() if isinstance(domain_info.expiration_date, datetime) else str(domain_info.expiration_date),
            "days_since_creation": days_since_creation
        }
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"도메인 '{domain_name}' 정보를 조회할 수 없습니다: {e}")

@app.get("/report/domain/{domain_name}")
async def get_domain_report(domain_name: str):
    """VirusTotal에서 도메인 리포트를 조회하는 API"""
    if not VT_API_KEY:
        raise HTTPException(status_code=503, detail="서버에 VirusTotal API 키가 설정되지 않았습니다.")
    
    headers = {"x-apikey": VT_API_KEY}
    
    try:
        response = requests.get(f"{VT_API_URL}/domains/{domain_name}", headers=headers)
        
        if response.status_code == 404:
            return {"positives": 0, "total": 0, "error": "Not found"}

        response.raise_for_status()
        data = response.json()
        
        stats = data['data']['attributes']['last_analysis_stats']
        positives = stats.get('malicious', 0) + stats.get('suspicious', 0)
        total = sum(stats.values())
        
        return {"positives": positives, "total": total}

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else 500
        raise HTTPException(status_code=status_code, detail=f"VirusTotal 도메인 분석 오류: {e}")


@app.get("/report/file/{file_hash}")
async def get_file_report(file_hash: str):
    """VirusTotal에서 파일 해시 리포트를 조회하는 API"""
    if not VT_API_KEY:
        raise HTTPException(status_code=503, detail="서버에 VirusTotal API 키가 설정되지 않았습니다.")
    
    headers = {"x-apikey": VT_API_KEY}
    
    try:
        response = requests.get(f"{VT_API_URL}/files/{file_hash}", headers=headers)
        
        if response.status_code == 404:
            return {"positives": 0, "total": 0, "error": "Not found"}

        response.raise_for_status()
        data = response.json()
        
        stats = data['data']['attributes']['last_analysis_stats']
        positives = stats.get('malicious', 0) + stats.get('suspicious', 0)
        total = sum(stats.values())
        
        return {"positives": positives, "total": total}

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else 500
        raise HTTPException(status_code=status_code, detail=f"VirusTotal 파일 분석 오류: {e}")


# --- 서버 실행 (uvicorn) ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)   