import requests
import zipfile
import os
from io import BytesIO
from bs4 import BeautifulSoup
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import Dict, Any, Optional, List

# .env 파일 로드
load_dotenv()

class DartCrawler:
    def __init__(self):
        self.api_key = os.getenv('DART_API_KEY')
        self.db_config = {
            'host': os.getenv('host'),
            'user': os.getenv('USER'),
            'password': os.getenv('PASWD'),
            'port': int(os.getenv('port')),
            'database': 'DART_DB'
        }
        self.base_url = "https://opendart.fss.or.kr/api"
        self.init_database()
        self.api_call_count = 0  # ✅ API 호출 횟수 관리

    def init_database(self):
        """MySQL 테이블 초기화"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()

        # 기업 리스트 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_list (
            corp_code VARCHAR(8) PRIMARY KEY,
            corp_name VARCHAR(255),
            stock_code VARCHAR(6),
            modify_date VARCHAR(8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 기업 상세 정보 테이블 생성
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_info (
            corp_code VARCHAR(8) PRIMARY KEY,
            corp_name VARCHAR(255),
            corp_name_eng VARCHAR(255),
            stock_code VARCHAR(6),
            business_number VARCHAR(12),
            ceo_name VARCHAR(255),
            corp_cls VARCHAR(1),
            jurir_no VARCHAR(13),
            establishment_date VARCHAR(8),
            acc_mt VARCHAR(2),
            address TEXT,
            homepage VARCHAR(255),
            phone_number VARCHAR(20),
            fax_number VARCHAR(20),
            total_assets BIGINT,
            net_income BIGINT,
            revenue BIGINT,
            operating_profit BIGINT,
            bsns_year VARCHAR(4),
            reprt_code VARCHAR(5),
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def fetch_and_store_corp_list(self):
        """OpenDART API에서 기업 리스트를 가져와 MySQL에 저장 (API 호출 1회)"""
        url = f"{self.base_url}/corpCode.xml"
        params = {'crtfc_key': self.api_key}

        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"기업 목록 조회 실패: {response.status_code}")

        with zipfile.ZipFile(BytesIO(response.content)) as z:
            with z.open(z.namelist()[0]) as f:
                xml_content = f.read()

        soup = BeautifulSoup(xml_content, 'xml')
        corps = []

        for corp in soup.find_all('list'):
            stock_code = corp.find('stock_code').text.strip()
            if stock_code and stock_code.isdigit():
                corps.append((
                    corp.find('corp_code').text.strip(),
                    corp.find('corp_name').text.strip(),
                    stock_code,
                    corp.find('modify_date').text.strip()
                ))

        # MySQL에 배치 저장
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        sql = """
        INSERT INTO company_list (corp_code, corp_name, stock_code, modify_date)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            corp_name = VALUES(corp_name),
            stock_code = VALUES(stock_code),
            modify_date = VALUES(modify_date)
        """
        
        try:
            cursor.executemany(sql, corps)  # ✅ API 호출 1회 후 배치 저장
            conn.commit()
            print(f"✅ 총 {len(corps)}개의 기업 리스트 저장 완료!")
        except Exception as e:
            print(f"❌ 기업 리스트 저장 실패: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def get_corp_list_from_db(self, start_idx: int, end_idx: int) -> List[Dict[str, str]]:
        """MySQL에서 기업 목록을 조회"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)

        sql = """
        SELECT corp_code, corp_name, stock_code 
        FROM company_list 
        ORDER BY corp_code 
        LIMIT %s, %s
        """
        
        try:
            cursor.execute(sql, (start_idx, end_idx - start_idx))
            corps = cursor.fetchall()
            print(f"📌 MySQL에서 가져온 기업 수: {len(corps)}")
            return corps
        except Exception as e:
            print(f"❌ 기업 목록 조회 실패: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_company_info(self, corp_code: str) -> Dict[str, Any]:
        """기업 기본 정보 조회 (API 호출 제한 관리)"""
        if self.api_call_count >= 19950:  # ✅ API 제한 관리
            print("⚠️ API 일일 할당량 초과 방지. 요청 중단.")
            return {}

        url = f"{self.base_url}/company.json"
        params = {'crtfc_key': self.api_key, 'corp_code': corp_code}
        response = requests.get(url, params=params)

        self.api_call_count += 1  # ✅ API 호출 횟수 증가
        time.sleep(1.5)  # ✅ API 요청 간격 조절 (속도 제한 방지)

        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '000':
                return data
        return {}

    def process_companies(self, start_idx: int = 0, end_idx: Optional[int] = None):
        """기업 데이터 수집 및 저장 실행"""
        corps = self.get_corp_list_from_db(start_idx, end_idx)
        print(f"처리할 기업 수: {len(corps)}")

        current_year = str(datetime.now().year)

        for i, corp in enumerate(corps, 1):
            try:
                print(f"\n[{i}/{len(corps)}] {corp['corp_name']} 처리 중...")

                company_info = self.get_company_info(corp['corp_code'])
                if not company_info:
                    continue

                # MySQL 저장 생략 (가져온 정보 활용 가능)

            except Exception as e:
                print(f"❌ {corp['corp_name']} 처리 중 오류 발생: {e}")

if __name__ == "__main__":
    crawler = DartCrawler()

    # 기업 리스트를 OpenDART에서 가져와 MySQL에 저장 (최초 1회 실행)
    crawler.fetch_and_store_corp_list()

    # MySQL에서 기업 리스트를 가져와 API 호출 최적화하여 데이터 업데이트
    crawler.process_companies(start_idx=0, end_idx=4000)
