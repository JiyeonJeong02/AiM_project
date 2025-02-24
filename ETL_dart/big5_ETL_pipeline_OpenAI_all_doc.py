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
import gc

class BusinessAnalysisSystem:
    def __init__(self):
        """Initialize with API settings"""
        # Load environment variables
        load_dotenv()
        
        # DART API settings
        self.api_key = os.getenv('DART_API_KEY')
        if not self.api_key:
            raise ValueError("DART_API_KEY environment variable is not set")
            
        # OpenAI API settings
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        self.base_url = "https://opendart.fss.or.kr/api"
        self.companies = {
            "삼성전자": "005930",
            "SK하이닉스": "000660",
            "현대자동차": "005380",
            "NAVER": "035420",
            "카카오": "035720"
        }
        self.corp_codes = {}
        
        # Elasticsearch settings
        self.es_url = os.getenv("ELASTICSEARCH_URL")
        self.index_name = os.getenv("INDEX_NAME", "business_overview")

    def download_corp_codes(self):
        """Download company unique codes"""
        url = f"{self.base_url}/corpCode.xml"
        params = {"crtfc_key": self.api_key}
        
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
            
            print("Corporate code list downloaded successfully")
            
        except Exception as e:
            print(f"Error downloading corporate codes: {e}")
            raise

    def get_company_info(self, company_name, stock_code):
        """Get basic company information"""
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
                    "설립일": data.get("est_dt"),
                    "상장일": data.get("listing_dt"),
                    "업종": data.get("induty_code"),
                    "홈페이지": data.get("hm_url"),
                    "주소": data.get("adres")
                }
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving company info ({company_name}): {e}")
            return None

    def get_business_report(self, corp_code):
        """Retrieve business report information"""
        url = f"{self.base_url}/list.json"
        current_year = datetime.now().year
        
        reports_by_type = {}
        report_types = {
            'A': '사업보고서',
            'F': '반기보고서',
            'Q': '분기보고서'
        }
        
        for report_type in report_types.keys():
            params = {
                "crtfc_key": self.api_key,
                "corp_code": corp_code,
                "bgn_de": f"{current_year-1}0101",
                "end_de": datetime.now().strftime("%Y%m%d"),
                "pblntf_ty": report_type,
                "last_reprt_at": "Y"
            }
            
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "000" and data.get("list"):
                    reports_by_type[report_type] = data.get("list")[0]
                    print(f"Found {report_types[report_type]}: {data['list'][0].get('rpt_nm')}")
            except Exception as e:
                print(f"Error retrieving {report_types[report_type]}: {e}")
        
        # Priority: Annual > Semi-annual > Quarterly
        if 'A' in reports_by_type:
            return reports_by_type['A']
        elif 'F' in reports_by_type:
            return reports_by_type['F']
        elif 'Q' in reports_by_type:
            return reports_by_type['Q']
            
        return None

    def download_report(self, rcept_no):
        """Download business report document"""
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
                    raise ValueError("ZIP file is empty")
                
                xml_content = z.read(file_list[0]).decode('utf-8', errors='ignore')
                
                # Debug: Save XML file
                debug_dir = "debug"
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"report_{rcept_no}.xml")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                print(f"- XML file saved: {debug_file}")
                
                return xml_content
                
        except Exception as e:
            print(f"Error downloading report (rcept_no: {rcept_no}): {e}")
            return None

    def extract_section(self, xml_content):
        """Extract contents from major sections I and II"""
        try:
            print("Starting section extraction...")
            soup = BeautifulSoup(xml_content, 'xml')
            
            if not soup.find():
                print("Failed to parse XML content")
                return None
            
            section_patterns = [
                # 주요 섹션
                r"I\.?\s*회사의\s*개요",
                r"II\.?\s*사업의\s*내용",
                r"III\.?\s*재무에\s*관한\s*사항",
                r"IV\.?\s*이사의\s*경영진단\s*및\s*분석의견",
                r"V\.?\s*주주에\s*관한\s*사항",
                
                # 숫자로 시작하는 패턴
                r"1\.?\s*회사의\s*개요",
                r"2\.?\s*사업의\s*내용",
                r"3\.?\s*재무에\s*관한\s*사항",
                r"4\.?\s*이사의\s*경영진단",
                r"5\.?\s*주주에\s*관한\s*사항",
                
                # 하위 섹션
                r"가\.\s*업계의\s*현황",
                r"나\.\s*회사의\s*현황",
                r"다\.\s*사업부문별\s*현황",
                r"라\.\s*신규사업\s*등의\s*내용",
                r"마\.\s*조직도",
                r"바\.\s*재무상태\s*및\s*영업실적",
                
                # 주요 하위 키워드
                r"사업의\s*내용",
                r"주요\s*제품",
                r"매출\s*현황",
                r"시장\s*점유율",
                r"신규\s*사업",
                r"주요\s*고객",
                r"생산\s*능력",
                r"연구개발",
                r"시장\s*전망"
            ]
            
            contents = []
            for title in soup.find_all(['TITLE', 'SUBTITLE']):
                title_text = title.get_text(strip=True)
                print(f"Found title: {title_text}")
                
                for pattern in section_patterns:
                    if re.search(pattern, title_text, re.IGNORECASE):
                        print(f"Matched section: {title_text}")
                        current = title.find_next()
                        while current and current.name != 'TITLE':
                            if current.name in ['P', 'TABLE', 'SPAN', 'SUBTITLE']:
                                text = current.get_text(strip=True)
                                if text and len(text) > 5:
                                    contents.append(text)
                            current = current.find_next()
            
            if not contents:
                print("No content found in major sections")
                return None
            
            # Remove duplicates while preserving order
            cleaned_contents = []
            seen = set()
            for content in contents:
                normalized_content = ' '.join(content.split())
                if normalized_content not in seen:
                    cleaned_contents.append(content)
                    seen.add(normalized_content)
            
            final_text = "\n".join(cleaned_contents)
            print(f"Final extracted content length: {len(final_text)}")
            
            return final_text
            
        except Exception as e:
            print(f"Error in extract_section: {e}")
            return None

    def chunk_text(self, text, max_tokens=3000):
        """Split text into chunks of approximately max_tokens"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_token_estimate = len(word) * 1.3  # 토큰 개수 추정

            if current_length + word_token_estimate > max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_length = word_token_estimate
                else:
                    chunks.append(word)  # 단어가 너무 길다면 그대로 추가
            else:
                current_chunk.append(word)
                current_length += word_token_estimate

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        print(f"🔹 총 {len(chunks)}개의 청크 생성됨.")
        return chunks


    def summarize_text(self, text, company_name):
        """청크별 요약을 수행한 후, 최종적으로 전체 내용을 종합하여 요약"""
        if not text:
            return "No content to summarize"

        chunks = self.chunk_text(text, max_tokens=3000)
        partial_summaries = []

        # 1️⃣ 각 청크별 부분 요약 수행
        for i, chunk in enumerate(chunks):
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo-16k",
                        "messages": [
                            {"role": "system", "content": "당신은 기업의 구체적인 사업 내용을 설명하는 경영 컨설턴트입니다. 다음 텍스트에서 핵심 사업/제품/서비스스 내용을 구체적인 키워드와 수치를 포함해서 요약하세요."},
                            {"role": "user", "content": f"다음 텍스트의 핵심 내용을 요약해주세요:\n\n{chunk}"}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 5000
                    }
                )
                response.raise_for_status()
                partial_summaries.append(response.json()["choices"][0]["message"]["content"].strip())
            
            except Exception as e:
                print(f"Summarization error: {e}")
                partial_summaries.append("요약 처리 중 오류가 발생했습니다.")

        # 2️⃣ 부분 요약된 내용을 하나의 텍스트로 합치기
        combined_summary = "\n".join(partial_summaries)

        # 3️⃣ 전체 내용을 종합하여 최종 요약 수행
        try:
            final_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo-16k",
                    "messages": [
                    {"role": "system", "content": """당신은 기업의 구체적인 사업 내용을 설명하는 경영 컨설턴트입니다. 기업의 실제 진행 중인 사업과 제품을 구체적으로 설명하고, 각각의 핵심 특성이나 용도를 정확히 서술하십시오.

                    또한, 보고서에 포함된 정량적 데이터(평균 판매 가격, 출하량, 매출 비중 등)가 있을 경우 이를 중요한 정보로 반영하십시오. 하지만, 없는 경우 임의로 생성하지 마십시오.
                    
                    * 주의사항:
                    1. 실제 진행 중인 내용만 포함
                    2. 구체적인 제품/서비스/기술명 필수 포함
                    3. 정량적 데이터가 보고서에 있으면 포함하되, 없는 경우 생성하지 않음
                    4. 지나치게 일반적인 설명보다는 기업의 구체적인 상황을 반영
                    5. 각 문장은 내용이 분리된 리스트 형태인 개별 항목(-)으로 나누어 작성 

                    다음 형식으로 작성:

                    0. 전체 기업 내용 요약
                    - 해당 기업의 핵심 사업, 제품, 시장 동향을 종합적으로 요약.
                    - 보고서에서 제공하는 정량적 데이터(평균 판매 가격, 출하량, 매출 비중 등)가 있으면 포함하여 트렌드 분석.

                    1. 주요 제품 및 서비스
                    - 제품명과 서비스명을 구체적으로 명시하고, 해당 제품의 핵심 기능 및 용도를 설명.
                    - 시장 반응, 평균 판매 가격 변동, 매출 기여도 변화 등의 정량적 정보가 있으면 포함.

                    2. 주요 기술 및 인프라
                    - 사용된 기술의 핵심 특성과 해당 기술이 적용된 제품/서비스를 설명.
                    - 생산능력, 비용 절감 효과 등 관련된 수치적 변화가 있으면 포함.

                    3. 핵심 사업 영역
                    - 현재 진행 중인 주요 사업 활동을 설명하고, 향후 성장 전략이 아니라 현황에 초점을 맞춤.
                    - 시장 반응, 성장률, 매출 기여도 등의 정량적 데이터가 존재하는 경우 이를 강조 (% 수치가 있다면 중요 정보로 간주).

                    """},

                    {"role": "user", "content": f"다음은 {company_name}의 사업 관련 주요 내용입니다. 이 내용을 기반으로 위의 형식에 맞춰 전체적으로 재구성하여 요약하십시오:\n\n{combined_summary}"}
                ],
                    "temperature": 0.3,
                    "max_tokens": 4000
                }
            )
            final_response.raise_for_status()
            return final_response.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"Final summarization error: {e}")
            return "최종 요약 처리 중 오류가 발생했습니다."

    # def summarize_text(self, text, company_name):
    #     """Summarize text using GPT-3.5-Turbo with chunking"""
    #     if not text:
    #         return "No content to summarize"
        
    #     chunks = self.chunk_text(text, max_tokens=3000)
    #     summaries = []
        
    #     for chunk in chunks:
    #         try:
    #             response = requests.post(
    #                 "https://api.openai.com/v1/chat/completions",
    #                 headers={
    #                     "Authorization": f"Bearer {self.openai_api_key}",
    #                     "Content-Type": "application/json"
    #                 },
    #                 json={
    #                     "model": "gpt-3.5-turbo-16k",
    #                     "messages": [
    #                         {"role": "system", "content": """기업의 실제 진행 중인 사업과 제품을 구체적 키워드로 추출하고, 각각의 주요 특성이나 용도를 간단히 설명합니다.

    #                         ❌ 피해야 할 표현:
    #                         - "~를 강화할 예정"
    #                         - "~시장 진출 계획"
    #                         - "~전략을 추진"
    #                         - "~경쟁력 향상"

    #                         ✅ 바람직한 표현:
    #                         - "'제품명A': 고성능 프리미엄 스마트폰, 폴더블 디스플레이 탑재"
    #                         - "'서비스명B': AI 기반 번역 서비스, 109개 언어 지원"
    #                         - "'기술명C': 5나노 반도체 제조 공정, 모바일 AP 생산에 적용"

    #                         다음 형식으로 작성:

    #                         0. 전체 기업 내용 요약
    #                         - 주요 사업/제품/서비스 내용을 요약
                            
    #                         1. 주요 제품 및 서비스
    #                         - 주요 특성/용도 설명, 핵심 기능/특징 설명, 시장 반응 설명 

    #                         2. 주요 기술 및 인프라
    #                         - 적용 제품/용도 설명, 생산품목/능력 설명, 시장 반응 설명 

    #                         3. 핵심 사업 영역
    #                         - 실제 진행 중인 내용 설명, 현재 진행 단계/규모 설명

    #                         * 주의사항:
    #                         1. 실제 진행 중인 내용만 포함 (계획이나 전략 제외)
    #                         2. 구체적인 제품/서비스/기술명 필수 포함
    #                         3. 각 항목의 실제 특성이나 용도를 구체적으로로 설명"""},
    #                         {"role": "user", "content": f"다음 {company_name}의 사업보고서에서 현재 진행 중인 구체적인 사업과 제품을 추출하고, 각각의 주요 특성을 설명해주세요:\n\n{chunk}"}
    #                     ],
    #                     "temperature": 0.3,
    #                     "max_tokens": 3000
    #                 }
    #             )
    #             response.raise_for_status()
    #             summaries.append(response.json()["choices"][0]["message"]["content"].strip())
    #         except Exception as e:
    #             print(f"Summarization error: {e}")
    #             summaries.append("요약 처리 중 오류가 발생했습니다.")
        
    #     return "\n".join(summaries) if summaries else "요약 처리 중 오류가 발생했습니다."



    def process_company(self, company_name, stock_code):
        """Process a single company"""
        try:
            print(f"\nProcessing {company_name}...")
            corp_code = self.corp_codes.get(stock_code)
            if not corp_code:
                print(f"Corporate code not found for {company_name}")
                return None
            
            company_info = self.get_company_info(company_name, stock_code)
            if not company_info:
                print(f"Company info not found for {company_name}")
                return None
            
            report = self.get_business_report(corp_code)
            if not report:
                print(f"Business report not found for {company_name}")
                return None
            
            xml_content = self.download_report(report.get("rcept_no"))
            if not xml_content:
                print(f"Failed to download report for {company_name}")
                return None
            
            report_content = self.extract_section(xml_content)
            if not report_content:
                print(f"Failed to extract sections for {company_name}")
                return None
            
            summary = self.summarize_text(report_content, company_name)
            
            if "요약 처리 중 오류가 발생했습니다." in summary:
                print("Retrying with chunked summarization...")
                summary = self.summarize_text(report_content, company_name)
            
            return {
                "company_name": company_name,
                "company_info": company_info,
                "business_overview": report_content,
                "business_overview_summary": summary
            }
        except Exception as e:
            print(f"Error processing {company_name}: {e}")
            return None


    def upload_to_elasticsearch(self, company_data):
        """Upload data to Elasticsearch with update functionality"""
        print("\nStarting Elasticsearch upload process...")
        headers = {"Content-Type": "application/json"}
        
        company_name = company_data.get("company_name")
        business_overview_summary = company_data.get("business_overview_summary", "")
        original_content = company_data.get("business_overview", "")
        company_info = company_data.get("company_info", {})
        
        if not business_overview_summary:
            print(f"Warning: No summary data for {company_name}, skipping.")
            return
            
        print(f"Preparing data for {company_name}")
        doc = {
            "company_name": company_name,
            "business_overview_summary": business_overview_summary,
            "business_overview_original": original_content,
            "company_info": company_info,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Search for existing document
            search_response = requests.post(
                f"{self.es_url}/{self.index_name}/_search",
                json={
                    "query": {
                        "match": {
                            "company_name.keyword": company_name
                        }
                    }
                },
                headers=headers,
                timeout=30
            )
            
            search_result = search_response.json()
            hits = search_result.get('hits', {}).get('hits', [])
            
            if hits:
                # Update existing document
                doc_id = hits[0]['_id']
                print(f"Found existing document with ID: {doc_id}")
                response = requests.post(
                    f"{self.es_url}/{self.index_name}/_update/{doc_id}",
                    json={"doc": doc},
                    headers=headers,
                    timeout=30
                )
            else:
                # Create new document
                print("No existing document found, creating new one")
                response = requests.post(
                    f"{self.es_url}/{self.index_name}/_doc",
                    json=doc,
                    headers=headers,
                    timeout=30
                )
            
            if response.status_code in [200, 201]:
                print(f"Successfully {'updated' if hits else 'created'} data for {company_name}")
                print(f"Response: {response.json()}")
            else:
                print(f"Failed to {'update' if hits else 'create'} data for {company_name}")
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"Timeout occurred while uploading data for {company_name}")
        except requests.exceptions.ConnectionError:
            print(f"Connection error occurred while uploading data for {company_name}")
        except Exception as e:
            print(f"Error uploading to Elasticsearch: {e}")
        
        print("Upload process completed")

    def save_individual_result(self, company_data, output_dir="output"):
        """Save individual company result"""
        os.makedirs(output_dir, exist_ok=True)
        company_name = company_data["company_name"]
        file_path = os.path.join(output_dir, f"{company_name}_report.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(company_data, f, ensure_ascii=False, indent=2)
        print(f"Saved result for {company_name} to: {file_path}")

    def save_results(self, results, output_dir="output"):
        """Save results to JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save combined results
        combined_path = os.path.join(output_dir, "company_reports.json")
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nSaved combined results to: {combined_path}")
        
        # Save individual company results
        for company_data in results:
            self.save_individual_result(company_data)

    def run(self):
        """Main execution method"""
        results = []
        
        try:
            print("Starting business analysis system...")
            self.download_corp_codes()
            
            for company_name, stock_code in self.companies.items():
                try:
                    company_data = self.process_company(company_name, stock_code)
                    if company_data:
                        # Save data immediately after processing each company
                        self.upload_to_elasticsearch(company_data)
                        self.save_individual_result(company_data)
                        results.append(company_data)
                        
                except Exception as e:
                    print(f"Error processing {company_name}: {e}")
                    continue
            
            # Save final combined results
            self.save_results(results)
            print("\nProcessing completed successfully")
            
        except Exception as e:
            print(f"Fatal error in main execution: {e}")
            raise

def main():
    try:
        system = BusinessAnalysisSystem()
        system.run()
    except Exception as e:
        print(f"Program terminated with error: {e}")

if __name__ == "__main__":
    main()