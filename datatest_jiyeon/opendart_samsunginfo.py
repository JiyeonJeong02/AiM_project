import requests
import zipfile
import os
from io import BytesIO
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re  # 정규 표현식 사용
"""
# Trouble-Shooting

기존에는 TITLE 태그를 통해서, 관련 내용을 조회하려고 함. 구조를 이용한 코딩을 시도
-> TITLE이 제대로 찾아지지 않음.
=> extract_section("회사의 개요"), extract_section("사업의 개요")로 변경하여 정확한 TITLE을 찾도록 수정
=> XML 내에서 정확한 섹션명을 사용하여 검색 → 정확한 위치에서 데이터를 가져올 수 있었음
=> **섹션명이 다를 시 에러가 날 가능성이 있음. 앞으로 유의할 것**
/
본문또한, 기존에는 TITLE 태그를 찾고, P 태그만 검색했음. 이 경우 본문 내용이 TABLE, SPAN 태그에 포함된 경우 찾지 못함
=> find_all_next()를 사용하여 TITLE 태그 이후의 모든 P, TABLE, SPAN 태그의 내용을 검색
=> 즉, 본문 내용이 다양한 태그에 포함되어 있어도 빠짐없이 가져올 수 있게 수정됨
"""

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv('DART_API_KEY')

# 다운로드할 공시의 접수번호
rcept_no = '20240814003284'  # 삼성전자 반기보고서 예제

# API 요청 URL
url = "https://opendart.fss.or.kr/api/document.xml"

# 요청 파라미터
params = {
    'crtfc_key': API_KEY,
    'rcept_no': rcept_no
}

# 저장할 폴더 생성
save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

# API 요청 및 파일 다운로드
response = requests.get(url, params=params)
if response.status_code == 200:
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        file_list = z.namelist()
        print(f"📌 ZIP 내부 파일 목록: {file_list}")

        # 첫 번째 파일 자동 선택
        extracted_file = file_list[0]
        xml_path = os.path.join(save_dir, extracted_file)

        # 파일 저장
        with open(xml_path, "wb") as f:
            f.write(z.read(extracted_file))

        print(f"✅ 저장 완료: {xml_path}")

else:
    raise Exception(f"❌ 다운로드 실패: 상태 코드 {response.status_code}")

# XML 파일 로드 (UTF-8로 강제 변환)
with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
    xml_content = f.read()

# 🔹 BeautifulSoup을 사용한 XML 파싱 (XML 파서 적용)
soup = BeautifulSoup(xml_content, features="xml")

# 🔹 "회사 개요" 및 "사업 개요" 찾기
def extract_section(section_title):
    """
    특정 섹션 제목을 찾아서 다음에 나오는 본문 내용을 추출
    """
    # 정규 표현식을 사용하여 "사업의 개요"와 관련된 모든 TITLE을 찾음
    section = soup.find("TITLE", string=lambda text: text and re.search(rf"\d*\.*\s*{section_title}", text))
    if section:
        content = []
        for sibling in section.find_all_next():
            if sibling.name == "TITLE":  # 다음 섹션이 나오면 중단
                break
            if sibling.name in ["P", "TABLE", "SPAN"]:  # 본문 내용이 포함된 태그
                text = sibling.get_text(strip=True)  # 불필요한 공백 제거
                if text and text not in content:  # 중복 데이터 입력 방지
                    content.append(text)

        return "\n".join(content) if content else "해당 섹션의 본문을 찾을 수 없습니다."
    return "해당 섹션을 찾을 수 없습니다."

company_overview = extract_section("회사의 개요")  # 숫자 포함 여부 관계없이 검색
business_overview = extract_section("사업의 개요")  # 숫자 포함 여부 관계없이 검색

# 결과 출력
print("\n📌 [회사 개요]")
print(company_overview)

print("\n📌 [사업 개요]")
print(business_overview)
