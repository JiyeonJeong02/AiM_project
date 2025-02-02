import requests
import zipfile
import os
import json
import csv
import time
from io import BytesIO
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
import xml.etree.ElementTree as ET

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv("DART_API_KEY")

# 저장할 폴더 생성
save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

# 🔹 대기업 5개 선정 (KOSPI 대형주)
corp_codes = {
    "삼성전자": "00126380",
    "SK하이닉스": "00164779",
    "현대자동차": "00164742",
    "네이버": "00184036",
    "카카오": "00110098",
}

# 🔹 `reprt_code` 우선순위 (1분기 → 반기 → 3분기 → 사업)
REPORT_CODES = ["11013", "11012", "11014", "11011"]

# 🔹 API 요청 함수 (자동 재시도 추가)
def request_with_retry(url, params, max_retries=3, timeout=10):
    session = requests.Session()  # 🔴 세션 유지
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException:
            print(f"⚠️ 요청 실패 ({attempt+1}/{max_retries}) - 재시도 중...")
            time.sleep(5)  # 5초 대기 후 재시도

    return None  # 최대 재시도 후 실패하면 None 반환

# 🔹 기업 개요 정보 가져오기
def get_company_info(corp_code):
    url = "https://opendart.fss.or.kr/api/company.json"
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}

    response = request_with_retry(url, params)
    if response:
        data = response.json()
        if data["status"] == "000":
            return {
                "기업명": data.get("corp_name", "정보 없음"),
                "영문명": data.get("corp_name_eng", "정보 없음"),
                "설립일": data.get("est_dt", "정보 없음"),
                "대표자명": data.get("ceo_nm", "정보 없음"),
                "사업자등록번호": data.get("bizr_no", "정보 없음"),
                "법인등록번호": data.get("jurir_no", "정보 없음"),
                "업종": data.get("induty_code", "정보 없음"),
                "주권상장 여부": data.get("stock_name", "정보 없음"),
                "상장일": data.get("list_dt", "정보 없음"),
                "홈페이지": data.get("hm_url", "정보 없음"),
            }
    return {}  # 🔴 기본값 반환 (None 방지)

# 🔹 특정 기업의 최신 보고서 접수번호(rcept_no) 가져오기
def get_latest_rcept_no(corp_code):
    for reprt_code in REPORT_CODES:
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": API_KEY,
            "corp_code": corp_code,
            "bgn_de": "20240101",
            "end_de": "20241231",
            "reprt_code": reprt_code,
            "page_no": 1,
            "page_count": 10,
        }

        response = request_with_retry(url, params)
        if response:
            data = response.json()
            if "list" in data and len(data["list"]) > 0:
                for report in data["list"]:
                    if "감사보고서" not in report["report_nm"]:
                        return report["rcept_no"]

    return None  # 🔴 보고서 없음

# 🔹 특정 기업의 "사업 개요" 추출
def extract_business_overview(corp_name, corp_code):
    rcept_no = get_latest_rcept_no(corp_code)
    if not rcept_no:
        return None

    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": rcept_no}

    response = request_with_retry(url, params)
    if response:
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            file_list = z.namelist()
            extracted_file = file_list[0]
            xml_path = os.path.join(save_dir, extracted_file)

            with open(xml_path, "wb") as f:
                f.write(z.read(extracted_file))

    else:
        return None

    # XML 파일 로드
    with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
        xml_content = f.read()

    soup = BeautifulSoup(xml_content, features="xml")

    def extract_section(section_title):
        section = soup.find("TITLE", string=lambda text: text and re.search(rf"\d*\.*\s*{section_title}", text))
        if not section:
            return None

        content = []
        for sibling in section.find_all_next():
            if sibling.name == "TITLE":
                break
            if sibling.name in ["P", "TABLE", "SPAN", "DIV"]:
                text = sibling.get_text(strip=True)
                if text and text not in content:
                    content.append(text)

        return "\n".join(content) if content else None

    return extract_section("사업의 개요")

# 🔹 대기업 5개 대상 실행
all_data = []

for corp_name, corp_code in corp_codes.items():
    company_info = get_company_info(corp_code)
    business_overview = extract_business_overview(corp_name, corp_code)

    result = {
        **company_info,
        "사업 개요": business_overview if business_overview else "사업 개요 없음"
    }
    all_data.append(result)

    time.sleep(1)  # API 요청 제한 방지를 위해 1초 대기

# 🔹 CSV 파일로 저장
csv_filename = "대기업_회사_사업개요.csv"
with open(csv_filename, mode="w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=all_data[0].keys())
    writer.writeheader()
    writer.writerows(all_data)

print(f"📄 CSV 파일 저장 완료: {csv_filename}")
