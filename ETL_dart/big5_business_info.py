import requests
import json
import re
import os
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class DartAPIParser:
    def __init__(self):
        self.api_key = os.getenv('DART_API_KEY')
        if not self.api_key:
            raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
            
        self.base_url = "https://opendart.fss.or.kr/api"
        self.companies = {
            "삼성전자": "005930",
            "SK하이닉스": "000660",
            "현대자동차": "005380",
            "NAVER": "035420",
            "카카오": "035720"
        }
        self.corp_codes = {}
        
    def download_corp_codes(self):
        """기업 고유번호 목록 다운로드"""
        url = f"{self.base_url}/corpCode.xml"
        params = {
            "crtfc_key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            with zipfile.ZipFile(BytesIO(response.content)) as zf:
                xml_data = zf.read('CORPCODE.xml')
                
            root = ET.fromstring(xml_data)
            for company in root.findall('.//list'):
                corp_code = company.findtext('corp_code')
                stock_code = company.findtext('stock_code')
                if stock_code and stock_code.strip():
                    self.corp_codes[stock_code] = corp_code
                    
            print(f"기업고유번호 목록 다운로드 완료")
            
        except Exception as e:
            print(f"기업고유번호 목록 다운로드 중 오류 발생: {e}")
            raise

    def get_company_info(self, company_name, stock_code):
        """회사 기본 정보 조회"""
        url = f"{self.base_url}/company.json"
        params = {
            "crtfc_key": self.api_key,
            "stock_code": stock_code
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "000":
                return {
                    "기업명": data.get("corp_name"),
                    "영문명": data.get("corp_name_eng"),
                    "종목코드": data.get("stock_code"),
                    "대표자명": data.get("ceo_nm"),
                    "법인구분": data.get("corp_cls"),
                    "법인등록번호": data.get("jurir_no"),
                    "사업자등록번호": data.get("bizr_no"),
                    "설립일": data.get("est_dt"),
                    "상장일": data.get("listing_dt"),
                    "결산월": data.get("acc_mt"),
                    "업종": data.get("induty_code"),
                    "홈페이지": data.get("hm_url"),
                    "주소": data.get("adres")
                }
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"회사 정보 조회 중 오류 발생 ({company_name}): {e}")
            return None

    def download_report(self, rcept_no):
        """사업보고서 원문 다운로드"""
        url = f"{self.base_url}/document.xml"
        params = {
            "crtfc_key": self.api_key,
            "rcept_no": rcept_no
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                file_list = z.namelist()
                if not file_list:
                    raise ValueError("ZIP 파일이 비어있습니다.")
                
                xml_content = z.read(file_list[0]).decode('utf-8', errors='ignore')
                
                # 디버깅: XML 파일 저장
                debug_dir = "debug"
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"report_{rcept_no}.xml")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                print(f"- XML 파일 저장됨: {debug_file}")
                
                return xml_content
                
        except Exception as e:
            print(f"사업보고서 다운로드 중 오류 발생 (rcept_no: {rcept_no}): {e}")
            return None

    def extract_section(self, xml_content):
        """사업 관련 섹션 내용 추출"""
        soup = BeautifulSoup(xml_content, 'xml')
        
        # 검색할 섹션 패턴 정의
        business_patterns = {
            "사업개요": [
                r"사업의\s*개요",
                r"기업의\s*개요",
                r"회사의\s*개요",
                r"기업개요",
                r"사업개요"
            ],
            "주요사업": [
                r"주요\s*사업",
                r"주요제품",
                r"주요.*현황",
                r"사업의\s*내용",
                r"사업내용"
            ],
            "영업개황": [
                r"영업의\s*개황",
                r"영업\s*개황",
                r"사업의\s*현황"
            ]
        }
        
        # 모든 TITLE, SUBTITLE 태그 수집
        all_titles = soup.find_all(['TITLE', 'SUBTITLE'])
        print("\n발견된 모든 제목:")
        for title in all_titles:
            print(f"  - {title.get_text(strip=True)}")
        
        # 섹션 내용 수집
        contents = []
        
        for pattern_type, patterns in business_patterns.items():
            for pattern in patterns:
                for title in all_titles:
                    title_text = title.get_text(strip=True)
                    if re.search(pattern, title_text, re.IGNORECASE):
                        print(f"\n발견된 섹션: {title_text} (패턴: {pattern})")
                        
                        # 현재 섹션부터 다음 TITLE까지의 내용 수집
                        section_content = []
                        current = title.find_next()
                        
                        while current and current.name != 'TITLE':
                            if current.name in ['P', 'TABLE', 'SPAN', 'SUBTITLE']:
                                text = current.get_text(strip=True)
                                if text and len(text) > 5:  # 의미 있는 길이의 텍스트만 포함
                                    # 불필요한 참조 문구 제거
                                    if not any(skip in text for skip in ['참고하시기 바랍니다', '참조하시기 바랍니다']):
                                        section_content.append(text)
                            current = current.find_next()
                        
                        if section_content:
                            # 중복 제거 및 내용 정리
                            cleaned_content = []
                            for text in section_content:
                                if text not in cleaned_content:
                                    cleaned_content.append(text)
                            
                            contents.extend(cleaned_content)
        
        if not contents:
            print("- 사업 관련 섹션을 찾을 수 없습니다.")
            return None
        
        # 최종 중복 제거 및 내용 정리
        unique_contents = []
        for content in contents:
            if content not in unique_contents:
                unique_contents.append(content)
        
        print(f"- 총 {len(unique_contents)}개의 텍스트 블록 추출")
        return "\n".join(unique_contents)

    def get_business_report(self, corp_code):
        """사업보고서 조회"""
        url = f"{self.base_url}/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bgn_de": "20230101",
            "end_de": datetime.now().strftime("%Y%m%d"),
            "pblntf_ty": "A",
            "last_reprt_at": "Y"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"사업보고서 조회 중 오류 발생 (corp_code: {corp_code}): {e}")
            return None

    def process_all_companies(self):
        """모든 대상 기업의 정보 수집"""
        print("기업고유번호 목록 다운로드 중...")
        self.download_corp_codes()
        
        results = []
        for company_name, stock_code in self.companies.items():
            print(f"\n{company_name} 정보 수집 시작...")
            company_data = {
                "company_name": company_name,
                "company_info": None,
                "business_overview": None
            }
            
            # 1. 회사 기본 정보 조회
            print(f"- 기본 정보 조회 중... (종목코드: {stock_code})")
            company_info = self.get_company_info(company_name, stock_code)
            if company_info:
                company_data["company_info"] = company_info
                print(f"- 기본 정보 조회 완료")
                
                # 2. 기업고유번호로 변환
                corp_code = self.corp_codes.get(stock_code)
                if corp_code:
                    print(f"- 기업고유번호 확인: {corp_code}")
                    
                    # 3. 최근 사업보고서 조회
                    print(f"- 사업보고서 조회 중...")
                    business_reports = self.get_business_report(corp_code)
                    if business_reports and business_reports.get("list"):
                        latest_report = business_reports["list"][0]
                        rcept_no = latest_report.get("rcept_no")
                        print(f"- 사업보고서 발견: {latest_report.get('rpt_nm')} ({rcept_no})")
                        
                        # 4. 사업보고서 원문 다운로드
                        print(f"- 사업보고서 원문 다운로드 중...")
                        xml_content = self.download_report(rcept_no)
                        if xml_content:
                            # 5. 섹션 추출
                            print(f"- 섹션 추출 중...")
                            business_content = self.extract_section(xml_content)
                            if business_content:
                                company_data["business_overview"] = business_content
                                print(f"- 사업 관련 내용 추출 완료 (길이: {len(business_content)} 자)")
                            else:
                                print(f"- 사업 관련 내용을 찾을 수 없습니다.")
                        else:
                            print(f"- 사업보고서 원문을 다운로드할 수 없습니다.")
                    else:
                        print(f"- 사업보고서를 찾을 수 없습니다.")
                else:
                    print(f"- 기업고유번호를 찾을 수 없습니다.")
            else:
                print(f"- 회사 정보를 찾을 수 없습니다.")
            
            results.append(company_data)
            print(f"{company_name} 정보 수집 완료")
        
        return results

def save_results(results, output_dir="output"):
    """결과를 JSON 파일로 저장"""
    os.makedirs(output_dir, exist_ok=True)
    
    full_path = os.path.join(output_dir, "company_reports.json")
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n전체 결과가 저장되었습니다: {full_path}")
    
    for company_data in results:
        company_name = company_data["company_name"]
        file_name = f"{company_name}_report.json"
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(company_data, f, ensure_ascii=False, indent=2)
        print(f"개별 결과가 저장되었습니다: {file_path}")

def main():
    try:
        parser = DartAPIParser()
        results = parser.process_all_companies()
        save_results(results)
        
    except ValueError as e:
        print(f"오류: {e}")
    except Exception as e:
        print(f"예상치 못한 오류가 발생했습니다: {e}")
        raise

if __name__ == "__main__":
    main()