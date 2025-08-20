# api_server.py

from fastapi import FastAPI, HTTPException
from core.db_manager import DBManager
import os
import uvicorn
import whois
from datetime import datetime

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

@app.get("/domain_info/{domain_name}")
async def get_domain_info(domain_name: str):
    """도메인 Whois 정보를 조회하는 API"""
    try:
        domain_info = whois.whois(domain_name)

        # 도메인 생성일자 추출 (피싱 탐지에 핵심)
        creation_date = domain_info.creation_date

        # creation_date가 리스트 형태일 수 있음
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        # 생성 후 경과 시간 계산
        days_since_creation = (datetime.now() - creation_date).days if creation_date else -1

        print('----- [DEBUG] -----')
        print('domain_name: ', domain_info.domain_name)
        print('registrar: ', domain_info.registrar)
        print('creation_date: ', creation_date)
        print('expiration_date: ', domain_info.expiration_date)
        print('days_since_creation: ', days_since_creation)
        print('raw: ', domain_info)
        print('-'*30)

        return {
            "domain_name": domain_info.domain_name,
            "registrar": domain_info.registrar,
            "creation_date": creation_date,
            "expiration_date": domain_info.expiration_date,
            "days_since_creation": days_since_creation,
            "raw": domain_info # 전체 원본 데이터
        }
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"도메인 정보를 조회할 수 없습니다: {e}")
    


# --- 서버 실행 (uvicorn) ---
# 터미널에서 `python api_server.py`로 직접 실행할 수 있도록 추가
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)