"""
코드 번호 기준 자동 조회 코드
- 코드 번호 기준으로 자동 분기/반기/사업보고서 조회.
- 그 외 보고서는 모두 제외함 (filtering)

- 소기업 부터 조회 돼서, 분기/반기/사업보고서 모두 조회가 안되는 기업이 많음.
- 따라서 기업 정보 확인 불가.
- **대기업 위주 특정 코드만 불러와서 정보 조회하는 방향으로 변경.**
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

# 🔹 모든 기업의 `corp_code` 가져오기
def get_all_corp_codes():
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
            corp_codes[corp_name] = corp_code

        return corp_codes
    else:
        print("❌ 기업 코드 XML 다운로드 실패")
        return {}

# 🔹 특정 기업의 최신 보고서 접수번호(rcept_no) 가져오기 (감사보고서 필터링)
def get_latest_rcept_no(corp_code):
    for reprt_code in REPORT_CODES:  
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            'crtfc_key': API_KEY,
            'corp_code': corp_code,
            'bgn_de': '20240101',
            'end_de': '20241231',
            'reprt_code': reprt_code,
            'page_no': 1,
            'page_count': 100
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'list' in data and len(data['list']) > 0:
                for report in data['list']:
                    if "감사보고서" not in report['report_nm']:  # 🔴 감사보고서 제외
                        print(f"📌 {corp_code}: {reprt_code} 보고서 선택됨 ({report['report_nm']})")
                        return report['rcept_no']
    
    return None

# 🔹 특정 기업의 "사업 개요" 추출
def extract_business_overview(corp_name, corp_code):
    rcept_no = get_latest_rcept_no(corp_code)
    if not rcept_no:
        print(f"⚠️ {corp_name}({corp_code})의 1분기/반기/3분기/사업보고서를 찾을 수 없습니다.")
        return None

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
        return None

    # XML 파일 로드
    with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
        xml_content = f.read()

    soup = BeautifulSoup(xml_content, features="xml")

    # 특정 섹션 추출 함수
    def extract_section(section_title):
        section = soup.find("TITLE", string=lambda text: text and re.search(rf"\d*\.*\s*{section_title}", text))
        if not section:
            return "해당 섹션을 찾을 수 없습니다."

        content = []
        for sibling in section.find_all_next():
            if sibling.name == "TITLE":
                break
            if sibling.name in ["P", "TABLE", "SPAN", "DIV"]:
                text = sibling.get_text(strip=True)
                if text and text not in content:
                    content.append(text)

        return "\n".join(content) if content else "해당 섹션의 본문을 찾을 수 없습니다."

    business_overview = extract_section("사업의 개요")
    return business_overview

# 🔹 보고서가 있는 기업만 저장
corp_codes = get_all_corp_codes()  # 모든 기업의 `corp_code` 가져오기

valid_data = []
for corp_name, corp_code in list(corp_codes.items())[:50]:  # 처음 50개 기업만 테스트
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
