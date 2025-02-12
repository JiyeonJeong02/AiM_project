import json
import requests
import os
from dotenv import load_dotenv

# ✅ .env 파일 로드
load_dotenv()

# ✅ 환경 변수 가져오기
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
KIBANA_URL = os.getenv("KIBANA_URL")
INDEX_NAME = os.getenv("INDEX_NAME", "business_overview")  # 기본값 설정

# ✅ JSON 파일 경로
JSON_FILE_PATH = "output/company_reports_summarized.json"

def load_json_data(file_path):
    """ JSON 파일을 로드하여 리스트로 반환 """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def upload_to_elasticsearch(data):
    """ Elasticsearch에 데이터 업로드 """
    headers = {"Content-Type": "application/json"}

    for company in data:
        company_name = company.get("company_name")
        business_overview_summary = company.get("business_overview_summary", "")

        if not business_overview_summary:
            print(f"⚠ {company_name}의 요약 데이터가 없습니다. 건너뜀.")
            continue

        doc = {
            "company_name": company_name,
            "business_overview_summary": business_overview_summary
        }

        # ✅ Elasticsearch에 문서 저장
        response = requests.post(f"{ELASTICSEARCH_URL}/{INDEX_NAME}/_doc", json=doc, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"✅ {company_name} 데이터 저장 완료!")
        else:
            print(f"❌ {company_name} 데이터 저장 실패! {response.text}")

if __name__ == "__main__":
    json_data = load_json_data(JSON_FILE_PATH)
    upload_to_elasticsearch(json_data)
