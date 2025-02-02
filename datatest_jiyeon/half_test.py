import requests
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv('DART_API_KEY')

# 조회할 기업의 고유번호 (예: 삼성전자)
corp_code = '00126380'  # 삼성전자의 고유번호 예시

# 조회할 사업연도
bsns_year = '2024'

# 조회할 보고서 코드 (반기보고서: 11012, 분기보고서: 11013)
reprt_code = '11012'

# API 요청 URL
url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"

# 요청 파라미터
params = {
    'crtfc_key': API_KEY,
    'corp_code': corp_code,
    'bsns_year': bsns_year,
    'reprt_code': reprt_code
}

# API 요청
response = requests.get(url, params=params)

# 응답 확인
if response.status_code == 200:
    data = response.json()
    if data['status'] == '000':
        # 정상 응답
        print("📄 재무제표 데이터:", data['list'])
    else:
        print(f"⚠️ 오류 발생: {data['message']}")
else:
    print(f"❌ 요청 실패: 상태 코드 {response.status_code}")




"""
반기보고서 주요 재무 데이터 추출 코드
"""
import json

# JSON 데이터 (실제 실행 시 API 응답 데이터 변수에 저장된 값 사용)
data = [
    {"account_nm": "자산총계", "thstrm_amount": "485,757,698,000,000", "frmtrm_amount": "455,905,980,000,000", "sj_div": "BS"},
    {"account_nm": "부채총계", "thstrm_amount": "102,231,027,000,000", "frmtrm_amount": "92,228,115,000,000", "sj_div": "BS"},
    {"account_nm": "자본총계", "thstrm_amount": "383,526,671,000,000", "frmtrm_amount": "363,677,865,000,000", "sj_div": "BS"},
    {"account_nm": "매출액", "thstrm_amount": "74,068,302,000,000", "frmtrm_amount": "60,005,533,000,000", "sj_div": "IS"},
    {"account_nm": "영업이익", "thstrm_amount": "10,443,878,000,000", "frmtrm_amount": "668,547,000,000", "sj_div": "IS"},
    {"account_nm": "당기순이익", "thstrm_amount": "9,841,345,000,000", "frmtrm_amount": "1,723,571,000,000", "sj_div": "IS"}
]

# 📌 데이터 정리
financial_summary = {
    "자산총계": None,
    "부채총계": None,
    "자본총계": None,
    "매출액": None,
    "영업이익": None,
    "당기순이익": None
}

# 데이터 필터링 및 정리
for item in data:
    if item["account_nm"] in financial_summary:
        financial_summary[item["account_nm"]] = {
            "현재 반기": item["thstrm_amount"],
            "이전 기말": item["frmtrm_amount"]
        }

# 결과 출력
print("\n📌 삼성전자 2024 반기보고서 요약")
for key, value in financial_summary.items():
    print(f"{key}: {value['현재 반기']} (전기말: {value['이전 기말']})")
