import os
import sys  # ✅ 명령줄 인자 처리 추가
import json
import requests
import logging
import zipfile
from io import BytesIO
from typing import List, Dict
from datetime import datetime
import time
from dotenv import load_dotenv
from transformers import pipeline, AutoTokenizer
import xml.etree.ElementTree as ET
import os


# 보고서 확인 용
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
# 디버깅 용
DEBUG_DIR = "debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


# 로그 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DartETLPipeline:
    def __init__(self, batch_size=10, daily_api_limit=1000):
        """DART ETL 파이프라인 초기화"""
        load_dotenv()
        self.api_key = os.getenv("DART_API_KEY")
        self.es_url = os.getenv("ELASTICSEARCH_URL")
        self.index_name = os.getenv("INDEX_NAME", "business_overview")

        if not self.api_key:
            raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다.")
        if not self.es_url:
            raise ValueError("ELASTICSEARCH_URL 환경 변수가 설정되지 않았습니다.")

        self.base_url = "https://opendart.fss.or.kr/api"
        self.batch_size = batch_size
        self.daily_api_limit = daily_api_limit
        self.api_call_count = 0

        # 통계 변수
        self.total_companies = 0
        self.skipped_companies = 0
        self.successful_uploads = 0
        self.failed_uploads = 0

        # KoBART 모델 로드
        logger.info("KoBART 요약 모델 로드 중...")
        self.model_name = "digit82/kobart-summarization"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.summarizer = pipeline("summarization", model=self.model_name, tokenizer=self.tokenizer)
        logger.info("KoBART 모델 로드 완료.")

    def test_elasticsearch_connection(self) -> bool:
        """Elasticsearch 연결 테스트"""
        try:
            response = requests.get(self.es_url, timeout=10)
            logger.info(f"Elasticsearch 연결 상태 코드: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Elasticsearch 연결 실패: {e}")
            return False

    def get_corp_list(self, start_idx: int, end_idx: int) -> List[Dict]:
        """DART API에서 상장사 목록 가져오기 (corpCode.xml을 output 폴더에 저장)"""
        url = f"{self.base_url}/corpCode.xml"
        params = {'crtfc_key': self.api_key}

        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                return []

            file_path = os.path.join(OUTPUT_DIR, "corpCode.xml")  # ✅ output 폴더에 저장
            with open(file_path, "wb") as f:
                f.write(response.content)
            logger.info(f"📂 기업 코드 XML 데이터 저장 완료: {file_path}")

            with zipfile.ZipFile(BytesIO(response.content)) as z:
                xml_data = z.read(z.namelist()[0])

            root = ET.fromstring(xml_data)
            all_corp_list = [
                {
                    'corp_code': corp.findtext('corp_code'),
                    'corp_name': corp.findtext('corp_name'),
                    'stock_code': corp.findtext('stock_code', '').strip()
                }
                for corp in root.findall('.//list')
                if corp.findtext('stock_code')
            ]

            logger.info(f"📊 전체 기업 개수: {len(all_corp_list)}개")
            end_idx = min(end_idx, len(all_corp_list))  # 범위를 초과하지 않도록 조정
            selected_corps = all_corp_list[start_idx:end_idx]

            logger.info(f"🔢 선택된 기업 개수: {len(selected_corps)} (범위: {start_idx}~{end_idx})")
            return selected_corps

        except Exception as e:
            logger.error(f"기업 목록 조회 실패: {e}")
            return []
            
    def get_business_report(self, corp_code: str) -> str:
        """사업 보고서, 반기 보고서, 분기 보고서 중 가장 최신 보고서를 가져오기"""
        if self.api_call_count >= self.daily_api_limit:
            return ""

        url = f"{self.base_url}/list.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bgn_de': '20230101',  # ✅ 2023년 이후 보고서만 조회
            'end_de': datetime.now().strftime('%Y%m%d'),
            'pblntf_ty': 'A',
            'last_reprt_at': 'Y'
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                return ""

            data = response.json()

            # ✅ 특정 기업(삼성전자, SK하이닉스)의 응답 JSON 저장하여 확인
            if corp_code in ["00126380", "005930"]:  # 삼성전자, SK하이닉스 등
                file_path = os.path.join("debug", f"{corp_code}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"📂 {corp_code} JSON 데이터 저장 완료: {file_path}")

            if data.get("status") == "013":
                self.no_report_count += 1
                return ""

            # ✅ A001(사업보고서), A002(반기보고서), A003(분기보고서) 중 최신 보고서 선택
            preferred_order = ["A001", "A002", "A003"]
            latest_report = None

            for report_type in preferred_order:
                report = next((r for r in data.get('list', []) if r.get('pblntf_detail_ty') == report_type), None)
                if report:
                    latest_report = report
                    break

            if not latest_report:
                return ""

            rcept_no = latest_report['rcept_no']

            # XML 문서 다운로드 요청
            document_url = f"{self.base_url}/document.xml"
            doc_response = requests.get(document_url, params={'crtfc_key': self.api_key, 'rcept_no': rcept_no})

            if doc_response.status_code != 200:
                return ""

            self.api_call_count += 1

            with zipfile.ZipFile(BytesIO(doc_response.content)) as z:
                xml_filename = z.namelist()[0]
                xml_content = z.read(xml_filename).decode('utf-8')

            return xml_content

        except Exception:
            return ""


    def run(self, start_idx=2000, end_idx=3000):
        """ETL 실행 (기업별 개별 출력 제거 및 요약 통계만 출력)"""
        if not self.test_elasticsearch_connection():
            return
        
        self.no_report_count = 0  # ✅ 사업 보고서 없는 기업 개수 카운트 추가
        self.successful_uploads = 0
        self.failed_uploads = 0

        corps = self.get_corp_list(start_idx, end_idx)
        self.total_companies = len(corps)

        for corp in corps:
            text = self.get_business_report(corp['corp_code'])

            if not text.strip():
                continue  # ✅ 개별 기업 출력 제거

            summary = self.summarizer(text, max_length=500, min_length=100, do_sample=False)[0]['summary_text']
            corp['business_overview'] = text
            corp['summary'] = summary

            response = requests.post(f"{self.es_url}/{self.index_name}/_doc", json=corp, headers={"Content-Type": "application/json"})
            if response.status_code in [200, 201]:
                self.successful_uploads += 1
            else:
                self.failed_uploads += 1

        # ✅ 최종 요약 로그만 출력
        logger.info("✅ ETL 프로세스 완료")
        logger.info(f"📊 총 조회된 기업 수: {self.total_companies}")
        logger.info(f"✅ 업로드 성공: {self.successful_uploads}개")
        logger.info(f"⚠️ 업로드 실패: {self.failed_uploads}개")
        logger.info(f"🚫 사업 보고서 없음: {self.no_report_count}개")


    def download_corp_codes(self):
        """Download company unique codes and convert to UTF-8"""
        url = f"{self.base_url}/corpCode.xml"
        params = {"crtfc_key": self.api_key}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()

            with zipfile.ZipFile(BytesIO(response.content)) as zf:
                xml_data = zf.read('CORPCODE.xml').decode("euc-kr")  # ✅ EUC-KR → UTF-8 변환

            # ✅ UTF-8로 변환된 XML을 저장
            with open("output/corpCode_utf8.xml", "w", encoding="utf-8") as f:
                f.write(xml_data)

            root = ET.fromstring(xml_data)
            for company in root.findall('.//list'):
                corp_code = company.findtext('corp_code')
                stock_code = company.findtext('stock_code')
                if stock_code and stock_code.strip():
                    self.corp_codes[stock_code] = corp_code  # ✅ 기업 코드 저장

            print("Corporate code list downloaded and converted successfully")

        except Exception as e:
            print(f"Error downloading corporate codes: {e}")
            raise

    import xml.etree.ElementTree as ET

    def get_samsung_corp_code(self):
        """삼성전자의 corp_code 확인"""
        stock_code = "005930"  # 삼성전자의 종목코드
        corp_code = self.corp_codes.get(stock_code)

        if corp_code:
            print(f"✅ 삼성전자의 corp_code: {corp_code}")
        else:
            print("❌ 삼성전자의 corp_code를 찾을 수 없음!")


    

if __name__ == "__main__":
    pipeline = DartETLPipeline(batch_size=10, daily_api_limit=1000)
    pipeline.run(start_idx=1000, end_idx=1500)  # ✅ 20개 기업만 처리
