import requests
import zipfile
import os
from io import BytesIO
from bs4 import BeautifulSoup
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import Dict, Any, Optional
import json

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
        
    def get_corp_list(self, start_idx: int = 0, end_idx: Optional[int] = None) -> list:
        """기업 목록 조회"""
        url = f"{self.base_url}/corpCode.xml"
        params = {'crtfc_key': self.api_key}
        
        print(f"API KEY: {self.api_key}")  # API 키 확인
        print("기업 목록 다운로드 중...")
        response = requests.get(url, params=params)
        print(f"응답 상태 코드: {response.status_code}")  # 응답 상태 확인
        
        if response.status_code != 200:
            raise Exception(f"기업 목록 조회 실패: {response.status_code}")
            
        # ZIP 파일 처리
        print("ZIP 파일 압축 해제 중...")
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            if not z.namelist():
                raise Exception("ZIP 파일이 비어있습니다.")
            print(f"ZIP 파일 내용: {z.namelist()}")
            with z.open(z.namelist()[0]) as f:
                xml_content = f.read()
                
        print("XML 파싱 중...")
        soup = BeautifulSoup(xml_content, 'xml')
        corps = []
        
        # 전체 기업 목록
        print("기업 목록 필터링 중...")
        all_corps = soup.find_all('list')
        
        # XML 내용 샘플 출력
        print("\nXML 내용 샘플:")
        print(xml_content[:1000])  # 처음 1000바이트만 출력
        
        if not all_corps:
            raise Exception("기업 목록을 찾을 수 없습니다.")
            
        print(f"\n전체 기업 수: {len(all_corps)}")
        print(f"샘플 기업 데이터:")
        for i in range(min(5, len(all_corps))):
            corp = all_corps[i]
            print(f"\n기업 {i+1}:")
            print(corp.prettify())
        
        # 인덱스 조정
        if end_idx is None:
            end_idx = len(all_corps)
            
        # 주식코드가 있는 기업만 필터링 (상장사만)
        skipped_count = 0
        for corp in all_corps[start_idx:end_idx]:
            try:
                corp_code = corp.find('corp_code').text.strip()
                corp_name = corp.find('corp_name').text.strip()
                stock_code = corp.find('stock_code').text.replace(" ", "").strip()  # 공백 제거 추가
                modify_date = corp.find('modify_date').text.strip()
                
                if stock_code and len(stock_code) == 6 and stock_code.isdigit():  # 숫자 여부 확인 추가
                    corps.append({
                        'corp_code': corp_code,
                        'corp_name': corp_name,
                        'stock_code': stock_code,
                        'modify_date': modify_date
                    })
                else:
                    skipped_count += 1
                    if skipped_count <= 5:  # 처음 5개의 건너뛴 기업만 출력
                        print(f"\n건너뛴 기업 {skipped_count}:")
                        print(f"기업명: {corp_name}")
                        print(f"종목코드: '{stock_code}'")  # 종목코드 값 확인용
                        print(f"기업코드: {corp_code}")
            except Exception as e:
                print(f"기업 데이터 처리 중 오류: {e}")
                print(f"문제된 데이터: {corp}")
                continue
        
        print(f"\n상장사 수: {len(corps)}")
        print(f"건너뛴 기업 수: {skipped_count}")
        
        if len(corps) > 0:
            print("\n첫 5개 상장사 정보:")
            for i, corp in enumerate(corps[:5]):
                print(f"\n상장사 {i+1}:")
                print(f"기업명: {corp['corp_name']}")
                print(f"종목코드: {corp['stock_code']}")
                print(f"기업코드: {corp['corp_code']}")
        return corps

    def get_company_info(self, corp_code: str) -> Dict[str, Any]:
        """기업 기본 정보 조회 (https://opendart.fss.or.kr/api/company.json)"""
        url = f"{self.base_url}/company.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if 'status' in data and data['status'] != '000':
                print(f"기업정보 조회 실패 ({corp_code}): {data.get('message', '')}")
                return {}
            return data
        except requests.exceptions.RequestException as e:
            print(f"기업정보 조회 중 오류 발생 ({corp_code}): {e}")
            return {}

    def get_financial_info(self, corp_code: str, bsns_year: str, reprt_code: str) -> Dict[str, Any]:
        """재무정보 조회 (https://opendart.fss.or.kr/api/fnlttSinglAcnt.json)"""
        url = f"{self.base_url}/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code,
            'fs_div': 'CFS'  # 연결재무제표
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if 'status' in data and data['status'] != '000':
                print(f"재무정보 조회 실패 ({corp_code}): {data.get('message', '')}")
                return {}
            return data
        except requests.exceptions.RequestException as e:
            print(f"재무정보 조회 중 오류 발생 ({corp_code}): {e}")
            return {}

    def save_to_database(self, data: Dict[str, Any]):
        """MySQL 데이터베이스에 데이터 저장"""
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        sql = """
        INSERT INTO company_info (
            corp_code, corp_name, stock_code,
            business_number, ceo_name, corp_cls, jurir_no,
            establishment_date, acc_mt, zip_code, address,
            homepage, phone_number, fax_number,
            total_assets, net_income, revenue, operating_profit,
            bsns_year, reprt_code,
            last_update, created_at, updated_at
        ) VALUES (
            %(corp_code)s, %(corp_name)s, %(stock_code)s,
            %(business_number)s, %(ceo_name)s, %(corp_cls)s, %(jurir_no)s,
            %(establishment_date)s, %(acc_mt)s, %(zip_code)s, %(address)s,
            %(homepage)s, %(phone_number)s, %(fax_number)s,
            %(total_assets)s, %(net_income)s, %(revenue)s, %(operating_profit)s,
            %(bsns_year)s, %(reprt_code)s,
            NOW(), NOW(), NOW()
        ) ON DUPLICATE KEY UPDATE
            corp_name = VALUES(corp_name),
            total_assets = VALUES(total_assets),
            net_income = VALUES(net_income),
            revenue = VALUES(revenue),
            operating_profit = VALUES(operating_profit),
            last_update = NOW(),
            updated_at = NOW()
        """
        
        try:
            cursor.execute(sql, data)
            conn.commit()
            return True
        except Exception as e:
            print(f"데이터베이스 저장 실패: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def process_companies(self, start_idx: int = 0, end_idx: Optional[int] = None):
        """기업 데이터 수집 및 저장 실행"""
        corps = self.get_corp_list(start_idx, end_idx)
        print(f"처리할 기업 수: {len(corps)}")
        
        current_year = str(datetime.now().year)
        
        for i, corp in enumerate(corps, 1):
            try:
                print(f"\n[{i}/{len(corps)}] {corp['corp_name']} 처리 중...")
                
                # 기업 기본 정보 조회
                time.sleep(1)  # API 호출 간격
                company_info = self.get_company_info(corp['corp_code'])
                if not company_info:
                    continue
                
                # 재무 정보 조회 (사업보고서)
                time.sleep(1)  # API 호출 간격
                financial_info = self.get_financial_info(
                    corp['corp_code'], 
                    current_year,
                    '11011'  # 사업보고서
                )
                
                # 데이터 통합
                data = {
                    'corp_code': corp['corp_code'],
                    'corp_name': corp['corp_name'],
                    'stock_code': corp['stock_code'],
                    'business_number': company_info.get('businessNumber'),
                    'ceo_name': company_info.get('ceoNm'),
                    'corp_cls': company_info.get('corpCls'),
                    'jurir_no': company_info.get('jurirNo'),
                    'establishment_date': company_info.get('estDt'),
                    'acc_mt': company_info.get('accMt'),
                    'zip_code': company_info.get('zipNo'),
                    'address': company_info.get('adres'),
                    'homepage': company_info.get('homepageUrl'),
                    'phone_number': company_info.get('phoneNumber'),
                    'fax_number': company_info.get('faxNumber'),
                    'total_assets': None,
                    'net_income': None,
                    'revenue': None,
                    'operating_profit': None,
                    'bsns_year': current_year,
                    'reprt_code': '11011'
                }
                
                # 재무 정보 추가
                if 'list' in financial_info:
                    for item in financial_info['list']:
                        if item.get('account_nm') == '자산총계':
                            data['total_assets'] = item.get('thstrm_amount')
                        elif item.get('account_nm') == '당기순이익':
                            data['net_income'] = item.get('thstrm_amount')
                        elif item.get('account_nm') == '매출액':
                            data['revenue'] = item.get('thstrm_amount')
                        elif item.get('account_nm') == '영업이익':
                            data['operating_profit'] = item.get('thstrm_amount')
                
                # 데이터베이스 저장
                if self.save_to_database(data):
                    print(f"✅ {corp['corp_name']} 데이터 처리 완료")
                else:
                    print(f"❌ {corp['corp_name']} 데이터베이스 저장 실패")
                
            except Exception as e:
                print(f"❌ {corp['corp_name']} 처리 중 오류 발생: {e}")
                continue

if __name__ == "__main__":
    crawler = DartCrawler()
    # 원하는 index의 기업만 처리
    crawler.process_companies(start_idx=1000, end_idx=5000)