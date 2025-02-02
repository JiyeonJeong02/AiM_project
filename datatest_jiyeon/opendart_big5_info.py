import requests
import zipfile
import os
import xml.etree.ElementTree as ET
from io import BytesIO
from bs4 import BeautifulSoup
import json
import time
import csv
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv("DART_API_KEY")

# 저장할 폴더 생성
save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

# 🔹 대기업 5개 선정 (KOSPI 대형주) (이름 기준으로 검색)
target_companies = ["삼성전자", "SK하이닉스", "현대자동차", "NAVER", "카카오"]

# 🔹 모든 기업의 `corp_code` 가져오기
def get_all_corp_codes():
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        with zipfile.ZipFile(BytesIO(response.content)) as zfile:
            zfile.extractall(save_dir)

        xml_path = os.path.join(save_dir, "corpCode.xml")
        tree = ET.parse(xml_path)
        root = tree.getroot()

        corp_codes = {}
        for corp in root.findall("list"):
            corp_name = corp.find("corp_name").text.strip()
            corp_code = corp.find("corp_code").text.strip()
            corp_codes[corp_name] = corp_code

        return corp_codes
    else:
        print("❌ 기업 코드 XML 다운로드 실패")
        return {}

# 🔹 최신 보고서 접수번호 (rcept_no) 가져오기 (한 번의 API 호출)
def get_latest_rcept_no(corp_codes):
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": API_KEY,
        "bgn_de": "20230101",  # 1년 동안의 최신 보고서 검색
        "end_de": "20241231",
        "page_no": 1,
        "page_count": 50
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        report_mapping = {}

        if "list" in data:
            for report in data["list"]:
                corp_code = report["corp_code"]
                report_name = report["report_nm"]
                rcept_no = report["rcept_no"]

                if corp_code in corp_codes.values() and "감사보고서" not in report_name:
                    report_mapping[corp_code] = rcept_no

        return report_mapping
    return {}

# 🔹 사업 개요 추출 (한 번의 API 호출)
def extract_business_overview(rcept_no):
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": rcept_no}

    response = requests.get(url)
    if response.status_code == 200:
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            file_list = z.namelist()
            extracted_file = file_list[0]
            xml_path = os.path.join(save_dir, extracted_file)

            with open(xml_path, "wb") as f:
                f.write(z.read(extracted_file))

    else:
        return None

    # XML 파일 로드 및 BeautifulSoup으로 파싱
    with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
        xml_content = f.read()

    soup = BeautifulSoup(xml_content, features="xml")

    def extract_section(section_title):
        section = soup.find("TITLE", string=lambda text: text and section_title in text)
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

    return extract_section("사업의 개요") or extract_section("사업 내용")

# 🔹 실행 과정
corp_codes = get_all_corp_codes()

# ✅ 네이버, 카카오 등 5개 기업의 실제 `corp_code` 확인
selected_corp_codes = {name: corp_codes[name] for name in target_companies if name in corp_codes}

# ✅ 5개 기업의 최신 보고서 접수번호 가져오기 (API 1회 호출)
latest_reports = get_latest_rcept_no(selected_corp_codes)

# ✅ 5개 기업의 기업 개요 및 사업 개요 가져오기 (API 1회 호출)
all_data = []

for corp_name, corp_code in selected_corp_codes.items():
    rcept_no = latest_reports.get(corp_code)
    business_overview = extract_business_overview(rcept_no) if rcept_no else "사업 개요 없음"

    # 기업 개요 정보 가져오기 (API 1회 호출)
    url = "https://opendart.fss.or.kr/api/company.json"
    params = {"crtfc_key": API_KEY, "corp_code": corp_code}

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "000":
            company_info = {
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
                "사업 개요": business_overview
            }
            all_data.append(company_info)

    time.sleep(1)  # API 요청 제한 방지를 위해 1초 대기

# 🔹 CSV 파일로 저장
csv_filename = "대기업_기업개요.csv"
with open(csv_filename, mode="w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=all_data[0].keys())
    writer.writeheader()
    writer.writerows(all_data)

print(f"📄 CSV 파일 저장 완료: {csv_filename}")
