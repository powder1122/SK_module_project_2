# setup_database.py
import pandas as pd
import sqlite3
import os

# --- 설정 변수 ---
# CSV 파일이 data 폴더 안에 있다고 가정합니다.
CSV_FILE_PATH = os.path.join('data', 'phishing_dataset.csv') 
# 생성할 DB 파일 경로. Quiz_Game.py가 참조하는 경로와 동일해야 합니다.
DB_FILE_PATH = os.path.join('data', 'quiz_questions.db')
TABLE_NAME = 'quiz_questions'


def setup_database():
    """
    CSV 파일에서 데이터를 읽어 SQLite 데이터베이스와 테이블을 생성하고 데이터를 삽입합니다.
    스크립트를 실행할 때마다 테이블을 삭제하고 새로 만들기 때문에 데이터가 중복되지 않습니다.
    """
    
    # 1. CSV 파일 읽기
    try:
        print(f"'{CSV_FILE_PATH}' 파일을 읽는 중...")
        df = pd.read_csv(CSV_FILE_PATH)
        print("파일 읽기 완료.")
    except FileNotFoundError:
        print(f"[오류] CSV 파일을 찾을 수 없습니다: '{CSV_FILE_PATH}'")
        print("스크립트와 같은 위치에 'data' 폴더를 만들고 그 안에 CSV 파일을 넣어주세요.")
        return

    # 2. 데이터베이스에 필요한 열만 선택하고, 열 이름 변경하기
    # CSV의 '해설' 열을 DB의 'explain' 열로 매핑합니다.
    required_columns = {
        'subject': 'subject',
        'body': 'body',
        'label': 'label',
        '해설': 'explain'  # '해설' 열의 이름을 'explain'으로 변경
    }
    
    # 실제 CSV 파일에 필요한 열이 모두 있는지 확인
    if not all(col in df.columns for col in required_columns.keys()):
        print("[오류] CSV 파일에 필요한 열이 부족합니다.")
        print(f"필수 열: {list(required_columns.keys())}")
        return
        
    df_clean = df[list(required_columns.keys())].rename(columns=required_columns)
    print("데이터 정제 및 열 이름 변경 완료.")

    # 3. 데이터베이스 연결 및 테이블 생성
    # DB가 저장될 data 폴더가 없으면 생성
    os.makedirs(os.path.dirname(DB_FILE_PATH), exist_ok=True)
    
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()
        print(f"데이터베이스 '{DB_FILE_PATH}'에 연결되었습니다.")
        
        # 기존에 테이블이 있다면 삭제 (중복 방지)
        print(f"기존 '{TABLE_NAME}' 테이블 삭제 중...")
        cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        
        # db_manager.py와 동일한 스키마로 새 테이블 생성
        print(f"새 '{TABLE_NAME}' 테이블 생성 중...")
        cursor.execute(f'''
            CREATE TABLE {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                body TEXT NOT NULL,
                label INTEGER NOT NULL,
                explain TEXT
            )
        ''')
        print("테이블 생성 완료.")
        
        # 4. Pandas DataFrame의 데이터를 SQL 테이블에 삽입
        print("데이터를 테이블에 삽입하는 중...")
        df_clean.to_sql(TABLE_NAME, conn, if_exists='append', index=False)
        
        conn.commit()
        print(f"🎉 데이터베이스 설정 완료! 총 {len(df_clean)}개의 데이터가 성공적으로 추가되었습니다.")

    except sqlite3.Error as e:
        print(f"[데이터베이스 오류] {e}")
    finally:
        if conn:
            conn.close()
            print("데이터베이스 연결이 종료되었습니다.")


# 이 스크립트가 직접 실행될 때만 setup_database() 함수를 호출
if __name__ == "__main__":
    setup_database()