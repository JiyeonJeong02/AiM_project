import os
import time
import json
import requests
import logging
import zipfile
import traceback
from io import BytesIO
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from transformers import pipeline, AutoTokenizer
import xml.etree.ElementTree as ET
import re

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
        """DART API에서 특정 범위의 기업 목록 가져오기"""
        url = f"{self.base_url}/corpCode.xml"
        params = {'crtfc_key': self.api_key}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()

            with zipfile.ZipFile(BytesIO(response.content)) as z:
                xml_data = z.read(z.namelist()[0])

            root = ET.fromstring(xml_data)
            corp_list = [
                {
                    'corp_code': corp.findtext('corp_code'),
                    'corp_name': corp.findtext('corp_name'),
                    'stock_code': corp.findtext('stock_code', '').strip()
                }
                for corp in root.findall('.//list')
                if corp.findtext('stock_code')
            ]

            return corp_list[start_idx:end_idx]

        except Exception as e:
            logger.error(f"기업 목록 조회 실패: {e}")
            return []

    def get_business_report(self, corp_code: str) -> str:
        """사업 보고서 원문 가져오기"""
        if self.api_call_count >= self.daily_api_limit:
            logger.warning("⚠️ 일일 API 호출 한도 초과. 중단합니다.")
            return ""

        url = f"{self.base_url}/list.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bgn_de': '20230101',
            'end_de': datetime.now().strftime('%Y%m%d'),
            'pblntf_ty': 'A',
            'last_reprt_at': 'Y'
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('list'):
                rcept_no = data['list'][0]['rcept_no']
                document_url = f"{self.base_url}/document.xml"
                doc_response = requests.get(document_url, params={'crtfc_key': self.api_key, 'rcept_no': rcept_no})
                doc_response.raise_for_status()
                self.api_call_count += 1

                with zipfile.ZipFile(BytesIO(doc_response.content)) as z:
                    xml_content = z.read(z.namelist()[0]).decode('utf-8')
                return xml_content
        except Exception as e:
            logger.error(f"{corp_code} 사업 보고서 조회 실패: {e}")
        return ""

    def summarize_text(self, text: str) -> str:
        """사업 개요 요약"""
        if not text:
            return ""
        try:
            return self.summarizer(text, max_length=500, min_length=100, do_sample=False)[0]['summary_text']
        except Exception as e:
            logger.error(f"요약 실패: {e}")
            return ""

    def is_corp_in_elasticsearch(self, corp_name: str) -> bool:
        """기업이 이미 Elasticsearch에 존재하는지 확인"""
        search_url = f"{self.es_url}/{self.index_name}/_search"
        headers = {"Content-Type": "application/json"}
        query = {"query": {"match": {"corp_name.keyword": corp_name}}}
        response = requests.post(search_url, json=query, headers=headers)

        try:
            data = response.json()
            return data.get("hits", {}).get("total", {}).get("value", 0) > 0
        except Exception as e:
            logger.error(f"Elasticsearch 조회 오류: {e}")
            return False

    def upload_to_elasticsearch(self, data: Dict):
        """Elasticsearch에 데이터 업로드"""
        if self.is_corp_in_elasticsearch(data["corp_name"]):
            logger.info(f"✅ {data['corp_name']} 이미 존재. 건너뜀.")
            return False

        doc_url = f"{self.es_url}/{self.index_name}/_doc"
        headers = {"Content-Type": "application/json"}
        response = requests.post(doc_url, json=data, headers=headers, timeout=10)

        if response.status_code in [200, 201]:
            logger.info(f"Elasticsearch 업로드 성공: {data['corp_name']}")
            return True
        logger.error(f"Elasticsearch 업로드 실패: {response.text}")
        return False

    def run(self, start_idx=0, end_idx=50):
        """ETL 실행"""
        if not self.test_elasticsearch_connection():
            return
        corps = self.get_corp_list(start_idx, end_idx)

        for corp in corps:
            text = self.get_business_report(corp['corp_code'])
            summary = self.summarize_text(text)
            corp['business_overview'] = text
            corp['summary'] = summary
            self.upload_to_elasticsearch(corp)

        logger.info("ETL 프로세스 완료")

if __name__ == "__main__":
    pipeline = DartETLPipeline(batch_size=10, daily_api_limit=15000)
    pipeline.run(start_idx=1500, end_idx=2000)  # 20개 기업만 처리
