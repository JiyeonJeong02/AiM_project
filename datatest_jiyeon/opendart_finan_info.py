import requests
import zipfile
import os
import csv
import time
from io import BytesIO
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv('DART_API_KEY')

# 저장할 폴더 생성
save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

# 🔹 반기(11012) 및 분기(11013) 보고서 코드
REPORT_CODES = {
    "반기": "11012",
    "분기": "11013"
}

# 🔹 기업 목록 (corp_code 리스트)
corp_codes = {
    "삼성전자": "00126380",
    "SK하이닉스": "00164779",  
    "현대자동차": "00164742"
}

# 🔹 특정 기업의 최신 접수번호 가져오기
def get_latest_rcept_no(corp_code):
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bgn_de': '20240101',
        'end_de': '20241231',
        'page_no': 1,
        'page_count': 10
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'list' in data:
            for report in data['list']:
                if report['report_nm'] in ["반기보고서", "분기보고서"]:
                    return report['rcept_no']
    except Exception as e:
        print(f"❌ [오류] 접수번호 조회 실패: {e}")
    
    return None

# 🔹 기업 개요 정보 가져오기 (API 호출 실패 시 기본값 제공)
def get_company_info(corp_code):
    url = "https://opendart.fss.or.kr/api/company.json"
    params = {'crtfc_key': API_KEY, 'corp_code': corp_code}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data['status'] == '000':
            return {
                "기업명": data.get('corp_name', '정보 없음'),
                "영문명": data.get('corp_name_eng', '정보 없음'),
                "설립일": data.get('est_dt', '정보 없음'),
                "대표자명": data.get('ceo_nm', '정보 없음'),
                "사업자등록번호": data.get('bizr_no', '정보 없음'),
                "법인등록번호": data.get('jurir_no', '정보 없음'),
                "업종": data.get('induty_code', '정보 없음'),
                "주권상장 여부": data.get('stock_name', '정보 없음'),
                "상장일": data.get('list_dt', '정보 없음'),
                "홈페이지": data.get('hm_url', '정보 없음')
            }
    except Exception as e:
        print(f"❌ [오류] 기업 개요 정보 조회 실패: {e}")

    return {}  # 🔴 기본값 반환 (None 방지)

# 🔹 기업 재무 정보 가져오기 (API 호출 실패 시 기본값 제공)
def get_financial_info(corp_code, report_code):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bsns_year': '2024',  # 최신 연도
        'reprt_code': report_code
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data['status'] == '000' and 'list' in data:
            financial_summary = {
                "자산총계": "정보 없음",
                "부채총계": "정보 없음",
                "자본총계": "정보 없음",
                "매출액": "정보 없음",
                "영업이익": "정보 없음",
                "당기순이익": "정보 없음"
            }
            for item in data['list']:
                if item["account_nm"] in financial_summary:
                    financial_summary[item["account_nm"]] = item["thstrm_amount"]
            return financial_summary
    except Exception as e:
        print(f"❌ [오류] 재무 정보 조회 실패: {e}")

    return {  # 🔴 기본값 반환 (None 방지)
        "자산총계": "정보 없음",
        "부채총계": "정보 없음",
        "자본총계": "정보 없음",
        "매출액": "정보 없음",
        "영업이익": "정보 없음",
        "당기순이익": "정보 없음"
    }

# 🔹 모든 기업의 보고서를 자동으로 다운로드 및 분석
all_data = []
for corp_name, corp_code in corp_codes.items():
    company_info = get_company_info(corp_code)
    financial_info = get_financial_info(corp_code, REPORT_CODES["반기"])

    if not company_info:
        print(f"⚠️ {corp_name}의 기업 개요 정보를 찾을 수 없습니다.")
        continue

    result = {
        **company_info,
        **financial_info
    }
    all_data.append(result)
    time.sleep(1)  # API 요청 제한 방지를 위해 1초 대기

# 🔹 결과를 CSV로 저장
csv_filename = "기업_반기_분기보고서_개요.csv"
with open(csv_filename, mode='w', encoding='utf-8-sig', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=all_data[0].keys())
    writer.writeheader()
    writer.writerows(all_data)

print(f"📄 CSV 저장 완료: {csv_filename}")
