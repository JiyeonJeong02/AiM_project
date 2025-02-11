# 큰 기업(코스피, 코스닥 상장기업 등) 위주로 먼저 조회
## 분기/반기/사업보고서가 없는 기업이 많아서. 테스트 용
"""
📌 해결 방법: 큰 기업부터 우선 조회
🚀 목표:
- 현재는 모든 기업의 corp_code를 조회하여 처리하는 방식
- 하지만 너무 작은 기업부터 조회되어 반기/분기/사업보고서가 없는 경우가 많음
- 큰 기업(코스피, 코스닥 상장기업 등) 위주로 먼저 조회하도록 개선
🔹 1. 해결 방법
✅ 1. Open DART API에서 기업의 "주권상장 여부"를 기준으로 필터링
    - company.json API를 활용하여 KOSPI/KOSDAQ 상장 기업 우선 조회
✅ 2. 상장기업 리스트를 우선적으로 가져오도록 정렬
✅ 3. Open DART의 list.json API에서 최근 보고서를 제출한 기업만 선택
✅ 4. 기업 규모(자산, 매출 등)를 기준으로 정렬하여 우선 처리
"""
import requests
import zipfile
import os
import json
import time
from io import BytesIO
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re
import xml.etree.ElementTree as ET

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv('DART_API_KEY')

# 저장할 폴더 생성
save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

# 🔹 `reprt_code` 우선순위 (1분기 → 반기 → 3분기 → 사업)
REPORT_CODES = ["11013", "11012", "11014", "11011"]

# 🔹 저장할 보고서 유형
VALID_REPORTS = ["반기보고서", "분기보고서", "사업보고서"]

# 🔹 KOSPI/KOSDAQ 상장기업 가져오기
def get_large_corp_codes():
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        with zipfile.ZipFile(BytesIO(response.content)) as zfile:
            zfile.extractall(save_dir)
        print("✅ 기업 코드 ZIP 다운로드 및 추출 완료.")

        xml_path = os.path.join(save_dir, "corpCode.xml")
        tree = ET.parse(xml_path)
        root = tree.getroot()

        corp_codes = {}
        for corp in root.findall("list"):
            corp_name = corp.find("corp_name").text.strip()
            corp_code = corp.find("corp_code").text.strip()
            stock_code = corp.find("stock_code").text.strip()  # 상장된 종목 코드

            if stock_code:  # 🔴 종목 코드가 있는 기업만 (즉, KOSPI/KOSDAQ 상장기업)
                corp_codes[corp_name] = corp_code

        return corp_codes
    else:
        print("❌ 기업 코드 XML 다운로드 실패")
        return {}

# 🔹 특정 기업의 최신 보고서 접수번호(rcept_no) 가져오기 (반기/분기/사업보고서만 선택)
def get_latest_rcept_nos(corp_code):
    valid_reports = []
    for reprt_code in REPORT_CODES:  
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            'crtfc_key': API_KEY,
            'corp_code': corp_code,
            'bgn_de': '20240101',
            'end_de': '20241231',
            'reprt_code': reprt_code,
            'page_no': 1,
            'page_count': 10
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'list' in data and len(data['list']) > 0:
                for report in data['list']:
                    if any(valid_name in report['report_nm'] for valid_name in VALID_REPORTS):  # 🔴 반기/분기/사업보고서만 선택
                        print(f"📌 {corp_code}: {reprt_code} 보고서 선택됨 ({report['report_nm']})")
                        valid_reports.append(report['rcept_no'])

    return valid_reports

# 🔹 특정 기업의 "사업 개요" 추출
def extract_business_overview(corp_name, corp_code):
    rcept_nos = get_latest_rcept_nos(corp_code)
    if not rcept_nos:
        print(f"⚠️ {corp_name}({corp_code})의 반기/분기/사업보고서를 찾을 수 없습니다.")
        return None

    extracted_contents = []
    for rcept_no in rcept_nos:
        # API 요청 URL
        url = "https://opendart.fss.or.kr/api/document.xml"
        params = {'crtfc_key': API_KEY, 'rcept_no': rcept_no}

        # API 요청 및 ZIP 파일 다운로드
        response = requests.get(url, params=params)
        if response.status_code == 200:
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                file_list = z.namelist()
                extracted_file = file_list[0]
                xml_path = os.path.join(save_dir, extracted_file)

                with open(xml_path, "wb") as f:
                    f.write(z.read(extracted_file))

            print(f"✅ {corp_name}({corp_code}) 보고서 저장 완료: {xml_path}")
        else:
            continue  # 다운로드 실패 시 다음 보고서로 진행

        # XML 파일 로드
        with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
            xml_content = f.read()

        soup = BeautifulSoup(xml_content, features="xml")

        # 특정 섹션 추출 함수
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

        business_overview = extract_section("사업의 개요")
        if business_overview:
            extracted_contents.append(business_overview)

    return "\n\n".join(extracted_contents) if extracted_contents else None

# 🔹 KOSPI/KOSDAQ 상장기업만 대상으로 실행
corp_codes = get_large_corp_codes()  # 🔴 상장기업 우선 조회

valid_data = []
for corp_name, corp_code in list(corp_codes.items())[:50]:  # 처음 50개 상장기업만 테스트
    print(f"\n📌 {corp_name}({corp_code}) - 최신 보고서 조회 중...")
    business_overview = extract_business_overview(corp_name, corp_code)

    if business_overview:
        valid_data.append({"기업명": corp_name, "사업 개요": business_overview})
    else:
        print(f"⚠️ {corp_name}의 보고서를 찾을 수 없음.")

    time.sleep(1)  # API 요청 제한 방지를 위해 1초 대기

# 5. JSON 파일 저장 (사업 개요가 있는 기업만)
with open("기업_사업개요.json", "w", encoding="utf-8") as f:
    json.dump(valid_data, f, ensure_ascii=False, indent=4)

print(f"📄 JSON 파일 저장 완료: 기업_사업개요.json")
