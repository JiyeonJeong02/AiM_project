import requests
import mysql.connector
import os
import time
from dotenv import load_dotenv
from typing import Dict, Any, List

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

    def get_total_corp_count(self) -> int:
        """MySQL에서 전체 기업 개수 가져오기"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        sql = "SELECT COUNT(*) FROM company_info"

        try:
            cursor.execute(sql)
            total_count = cursor.fetchone()[0]
            return total_count
        except Exception as e:
            print(f"❌ 전체 기업 개수 조회 실패: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def get_corp_list_from_db(self, start_idx: int, end_idx: int) -> List[Dict[str, str]]:
        """MySQL에서 특정 범위의 기업 리스트 가져오기"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        sql = """
        SELECT corp_code, corp_name 
        FROM company_info 
        ORDER BY corp_code 
        LIMIT %s, %s
        """
        try:
            cursor.execute(sql, (start_idx, end_idx - start_idx))
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"❌ 기업 목록 조회 실패: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_company_overview(self, corp_code: str) -> Dict[str, Any]:
        """기업개황 정보 조회 (DART API - 기업개황)"""
        url = f"{self.base_url}/company.json"
        params = {'crtfc_key': self.api_key, 'corp_code': corp_code}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'status' in data and data['status'] != '000':
                print(f"❌ 기업개황 조회 실패 ({corp_code}): {data.get('message', '')}")
                return {key: None for key in [
                    'business_number', 'jurir_no', 'ceo_name', 'corp_name_eng', 'est_dt',
                    'corp_cls', 'addr', 'hm_url', 'ir_url', 'phn_no', 'fax_no',
                    'induty_code', 'acc_mt', 'zip_code'
                ]}

            return {
                'business_number': data.get('bizr_no'),
                'jurir_no': data.get('jurir_no'),
                'ceo_name': data.get('ceo_nm'),
                'corp_name_eng': data.get('corp_name_eng'),
                'est_dt': data.get('est_dt'),
                'corp_cls': data.get('corp_cls'),
                'addr': data.get('adres'),
                'hm_url': data.get('hm_url'),
                'ir_url': data.get('ir_url'),
                'phn_no': data.get('phn_no'),
                'fax_no': data.get('fax_no'),
                'induty_code': data.get('induty_code'),
                'acc_mt': data.get('acc_mt'),
                'zip_code': data.get('zip_cd')
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ 기업개황 조회 중 오류 발생 ({corp_code}): {e}")
            return {key: None for key in [
                'business_number', 'jurir_no', 'ceo_name', 'corp_name_eng', 'est_dt',
                'corp_cls', 'addr', 'hm_url', 'ir_url', 'phn_no', 'fax_no',
                'induty_code', 'acc_mt', 'zip_code'
            ]}

    def save_batch_to_database(self, conn, data_list):
        """배치 업데이트를 통해 여러 기업 데이터를 한 번에 MySQL에 적재"""
        cursor = conn.cursor()
        sql = """
        UPDATE company_info
        SET
            business_number = %s,
            jurir_no = %s,
            ceo_name = %s,
            corp_name_eng = %s,
            est_dt = %s,
            corp_cls = %s,
            address = %s,
            homepage = %s,
            ir_url = %s,
            phone_number = %s,
            fax_number = %s,
            induty_code = %s,
            acc_mt = %s,
            zip_code = %s,
            last_update = NOW()
        WHERE corp_code = %s
        """
        try:
            cursor.executemany(sql, data_list)  # 여러 개의 데이터 한꺼번에 처리
            conn.commit()
            print(f"✅ {len(data_list)}개 기업 정보 배치 업데이트 완료")
        except Exception as e:
            print(f"❌ 기업 배치 업데이트 실패: {e}")
            conn.rollback()
        finally:
            cursor.close()

    def process_company_overviews(self, start_idx: int, end_idx: int):
        """MySQL에서 기업 리스트 조회 후 기업개황 정보 업데이트 (배치 저장 + 2초 대기)"""
        total_count = self.get_total_corp_count()
        corp_list = self.get_corp_list_from_db(start_idx, end_idx)

        if not corp_list:
            print("⚠️ 조회된 기업이 없습니다.")
            return

        conn = mysql.connector.connect(**self.db_config)  # MySQL 연결 유지
        batch_data = []

        for idx, corp in enumerate(corp_list, start=start_idx + 1):
            corp_code = corp['corp_code']
            corp_name = corp['corp_name']
            print(f"\n🔎 [{idx}/{total_count}] {corp_name} ({corp_code}) 기업개황 정보 수집 중...")

            overview_data = self.get_company_overview(corp_code)

            if overview_data:
                batch_data.append(tuple(overview_data.values()) + (corp_code,))

            # 5개 기업마다 배치 저장 & 2초 대기
            if idx % 5 == 0 and batch_data:
                self.save_batch_to_database(conn, batch_data)
                batch_data.clear()
                time.sleep(2)  # 2초 대기

        # 남아 있는 데이터 저장
        if batch_data:
            self.save_batch_to_database(conn, batch_data)

        conn.close()  # MySQL 연결 닫기

if __name__ == "__main__":
    crawler = DartCrawler()

    # 기업 데이터 업데이트 실행 (첫 100개 기업)
    start_idx = 0
    end_idx = 3835  

    crawler.process_company_overviews(start_idx, end_idx)
