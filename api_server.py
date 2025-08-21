# api_server.py

from fastapi import FastAPI, HTTPException, Header
from core.db_manager import DBManager
import os
import uvicorn
import whois
from datetime import datetime
import requests
import time

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

        # print('----- [DEBUG] -----')
        # print('domain_name: ', domain_info.domain_name)
        # print('registrar: ', domain_info.registrar)
        # print('creation_date: ', creation_date)
        # print('expiration_date: ', domain_info.expiration_date)
        # print('days_since_creation: ', days_since_creation)
        # print('raw: ', domain_info)
        # print('-'*30)

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

@app.post("/report/url")
async def get_url_report(url: str, x_vt_api_key: str = Header(...)):
    """VirusTotal에 URL을 분석 요청하고 결과를 반환하는 API"""
    if not x_vt_api_key:
        raise HTTPException(status_code=400, detail="VirusTotal API 키가 필요합니다.")
    
    headers = {"x-apikey": x_vt_api_key}
    
    try:
        # URL 분석 요청
        scan_response = requests.post(f"{VT_API_URL}/urls", headers=headers, data={"url": url})
        scan_response.raise_for_status()
        analysis_id = scan_response.json()['data']['id']
        
        # 분석 완료까지 대기 (최대 30초)
        report = None
        for _ in range(10):
            time.sleep(3)
            report_response = requests.get(f"{VT_API_URL}/analyses/{analysis_id}", headers=headers)
            if report_response.status_code == 200:
                report_data = report_response.json()
                if report_data['data']['attributes']['status'] == 'completed':
                    report = report_data
                    break
        
        if not report:
            raise HTTPException(status_code=408, detail="VirusTotal 분석 시간이 초과되었습니다.")

        stats = report['data']['attributes']['stats']
        positives = stats.get('malicious', 0) + stats.get('suspicious', 0)
        total = sum(stats.values())
        
        return {"positives": positives, "total": total}

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else 500
        raise HTTPException(status_code=status_code, detail=f"VirusTotal URL 분석 오류: {e}")


@app.get("/report/file/{file_hash}")
async def get_file_report(file_hash: str, x_vt_api_key: str = Header(...)):
    """VirusTotal에서 파일 해시 리포트를 조회하는 API"""
    if not x_vt_api_key:
        raise HTTPException(status_code=400, detail="VirusTotal API 키가 필요합니다.")
    
    headers = {"x-apikey": x_vt_api_key}
    
    try:
        response = requests.get(f"{VT_API_URL}/files/{file_hash}", headers=headers)
        
        # 파일이 VT에 없는 경우 404 오류 발생
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