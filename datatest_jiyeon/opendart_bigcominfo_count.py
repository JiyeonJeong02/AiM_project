import requests
import zipfile
import os
import json
import pandas as pd
import time
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# .env 파일 로드
load_dotenv()

# Open DART API 키 가져오기
API_KEY = os.getenv("DART_API_KEY")

# 저장할 폴더 생성
save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

# 🔹 `reprt_code` 우선순위 (1분기 → 반기 → 3분기 → 사업)
REPORT_CODES = {
    "1분기": "11013",
    "반기": "11012",
    "3분기": "11014",
    "사업": "11011",
}

# 🔹 병렬 처리 개수 설정 (한 번에 10개 기업씩 처리)
MAX_WORKERS = 10

# 🔹 특정 기간 (2024년도 데이터만 조회)
START_DATE = "20240101"
END_DATE = "20241231"

# 🔹 API 요청 함수 (자동 재시도 추가)
def request_with_retry(url, params, max_retries=3, timeout=10):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException:
            time.sleep(5)  # 5초 대기 후 재시도

    return None  # 최대 재시도 후 실패하면 None 반환

# 🔹 모든 기업의 `corp_code` 가져오기 (KOSPI/KOSDAQ 상장기업)
def get_large_corp_codes():
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}"
    response = request_with_retry(url, {})

    if response:
        zip_path = os.path.join(save_dir, "corpCode.zip")
        xml_path = os.path.join(save_dir, "corpCode.xml")

        # ZIP 파일 저장
        with open(zip_path, "wb") as f:
            f.write(response.content)

        # ZIP 파일 해제
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(save_dir)

        # XML 파일 로드
        tree = ET.parse(xml_path)
        root = tree.getroot()

        corp_codes = {}
        for corp in root.findall("list"):
            corp_name = corp.find("corp_name").text.strip()
            corp_code = corp.find("corp_code").text.strip()
            stock_code = corp.find("stock_code").text if corp.find("stock_code") is not None else ""

            if stock_code:  # 🔴 KOSPI/KOSDAQ 기업만 포함
                corp_codes[corp_name] = corp_code

        return corp_codes
    else:
        print("❌ 기업 코드 XML 다운로드 실패")
        return {}

# 🔹 특정 기업의 반기/분기/사업보고서 개수 조회 (병렬 처리 적용)
def get_report_counts(corp_code):
    report_counts = {key: 0 for key in REPORT_CODES.keys()}
    session = requests.Session()  # 🔴 세션을 사용하여 API 속도 최적화

    for report_type, reprt_code in REPORT_CODES.items():
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": API_KEY,
            "corp_code": corp_code,
            "bgn_de": START_DATE,  # 🔴 2024년 데이터만 조회
            "end_de": END_DATE,
            "reprt_code": reprt_code,
            "page_no": 1,
            "page_count": 10,  # 최신 보고서 10개까지 조회
        }

        response = request_with_retry(url, params)
        if response:
            data = response.json()
            if "list" in data:
                report_counts[report_type] = len(data["list"])

    return report_counts

# 🔹 병렬 처리로 빠르게 조회
def process_corp_reports(corp_name, corp_code):
    report_counts = get_report_counts(corp_code)

    return {
        "기업명": corp_name,
        "반기보고서": report_counts["반기"],
        "분기보고서": report_counts["1분기"] + report_counts["3분기"],
        "사업보고서": report_counts["사업"],
    }

# 🔹 KOSPI/KOSDAQ 기업을 대상으로 실행 (조회 기업 수 증가)
corp_codes = get_large_corp_codes()

# 🔹 기업 수의 1/4만 조회 (전체 기업 개수의 25%)
total_corp_count = len(corp_codes)
quarter_corp_count = total_corp_count // 4  # 전체 기업 수의 1/4만 선택

corp_codes_subset = dict(list(corp_codes.items())[:quarter_corp_count])  # 🔴 상위 25% 기업만 조회

report_summary = []
total_counts = {"반기": 0, "분기": 0, "사업": 0}  # 🔴 전체 합계 저장

# 🔴 병렬 처리 실행
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_corp = {executor.submit(process_corp_reports, corp_name, corp_code): corp_name for corp_name, corp_code in corp_codes_subset.items()}

    for future in as_completed(future_to_corp):
        corp_name = future_to_corp[future]
        try:
            result = future.result()

            # 🔴 합계 계산
            total_counts["반기"] += result["반기보고서"]
            total_counts["분기"] += result["분기보고서"]
            total_counts["사업"] += result["사업보고서"]

            report_summary.append(result)
        except Exception:
            pass  # 🔴 오류 발생 시 무시하고 다음 기업으로 진행

# 🔹 전체 합계를 데이터프레임에 추가
report_summary.append(
    {
        "기업명": "총합",
        "반기보고서": total_counts["반기"],
        "분기보고서": total_counts["분기"],
        "사업보고서": total_counts["사업"],
    }
)

# 🔹 CSV 파일로 저장
df = pd.DataFrame(report_summary)
csv_filename = "기업_보고서개수_2024_1분의1.csv"
df.to_csv(csv_filename, encoding="utf-8-sig", index=False)

print(f"📄 CSV 파일 저장 완료: {csv_filename}")
