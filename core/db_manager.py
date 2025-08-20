# core/db_manager.py
# 데이터베이스 관리 모듈
import sqlite3

class DBManager:
    """
    SQLite 데이터베이스를 관리하는 클래스입니다.
    퀴즈 문제 데이터를 불러오고 관리하는 기능을 제공합니다.
    Streamlit 환경에 맞게 개선되었습니다.
    """
    def __init__(self, db_path):
        """데이터베이스 경로를 인자로 받아 연결을 설정합니다."""
        # check_same_thread=False는 Streamlit과 같은 멀티스레드 환경에서 필수적입니다.
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            # 결과를 딕셔너리 형태로 받기 위해 row_factory를 설정합니다.
            self.conn.row_factory = sqlite3.Row
            self.create_table() # 테이블이 없으면 생성
        except sqlite3.Error as e:
            print(f"데이터베이스 연결 오류: {e}")
            self.conn = None

    def create_table(self):
        """
        퀴즈 문제 데이터를 저장할 테이블을 생성합니다.
        'explain' 컬럼이 추가되었습니다.
        """
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT,
                    body TEXT NOT NULL,
                    label INTEGER NOT NULL,
                    explain TEXT NOT NULL 
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"테이블 생성 오류: {e}")

    def get_all_questions(self):
        """
        데이터베이스에 있는 모든 퀴즈 문제를 불러옵니다.
        'explain' 컬럼을 포함하여 조회합니다.
        """
        if not self.conn:
            return []
        try:
            cursor = self.conn.cursor()
            # explain 컬럼을 포함하여 모든 데이터를 선택합니다.
            cursor.execute("SELECT id, subject, body, label, explain FROM quiz_questions")
            # row_factory 덕분에 바로 딕셔너리 리스트로 변환할 수 있습니다.
            questions = [dict(row) for row in cursor.fetchall()]
            return questions
        except sqlite3.Error as e:
            print(f"데이터 조회 오류: {e}")
            return []

    def close(self):
        """데이터베이스 연결을 닫습니다."""
        if self.conn:
            self.conn.close()