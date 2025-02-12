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
from transformers import pipeline, AutoTokenizer

class BusinessAnalysisSystem:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # DART API settings
        self.api_key = os.getenv('DART_API_KEY')
        if not self.api_key:
            raise ValueError("DART_API_KEY environment variable is not set")
            
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
        
        # KoAlpaca model setup
        print("Loading KoAlpaca model...")
        self.model_name = "beomi/polyglot-ko-12.8b-v1.1"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            device_map="auto"
        )
        print("Model loaded successfully")

    def generate_summary(self, text):
        """Generate summary using KoAlpaca"""
        prompt_template = """아래 기업 보고서의 핵심 내용을 600자 내외로 요약해주세요. 
        기업의 주요 사업 영역, 실적, 전략적 방향성을 포함해야 합니다.
        불필요한 반복이나 중복된 내용은 제외하고, 명확하고 간결하게 작성해주세요.

        보고서 내용:
        {text}

        요약:"""
        
        prompt = prompt_template.format(text=text)
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            inputs = inputs.to(self.model.device)
            
            outputs = self.model.generate(
                **inputs,
                max_length=3072,
                min_length=200,
                temperature=0.7,
                top_p=0.9,
                num_beam_groups=4,
                diversity_penalty=0.5,
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            summary = summary.replace(prompt, "").strip()
            return summary
            
        except Exception as e:
            print(f"Error in summary generation: {str(e)}")
            return None

    def summarize_text(self, text, company_name):
        """Summarize text using KoAlpaca with preprocessing"""
        print(f"\nStarting text summarization for {company_name}...")
        
        if not text:
            print("Error: Empty text received")
            return "No content to summarize"
            
        print(f"Original text length: {len(text)} characters")
        
        try:
            # Preprocess and clean text
            text = self.preprocess_text(text, company_name)
            text = self.clean_text(text)
            print("Text preprocessing and cleaning completed")
            
            # Split into chunks if too long
            max_chunk_length = 1500
            chunks = [text[i:i + max_chunk_length] for i in range(0, len(text), max_chunk_length)]
            print(f"Split text into {len(chunks)} chunks")
            
            summaries = []
            for i, chunk in enumerate(chunks, 1):
                print(f"\nProcessing chunk {i}/{len(chunks)}")
                summary = self.generate_summary(chunk)
                if summary:
                    summaries.append(summary)
            
            if not summaries:
                return "Summarization failed"
            
            # Combine summaries if multiple chunks
            if len(summaries) > 1:
                combined_text = " ".join(summaries)
                final_summary = self.generate_summary(combined_text)
            else:
                final_summary = summaries[0]
            
            # Clean up the final summary
            final_summary = self.clean_text(final_summary)
            final_summary = self.remove_duplicate_sentences(final_summary)
            
            print(f"Final summary length: {len(final_summary)} characters")
            return final_summary
            
        except Exception as e:
            print(f"Error in summarization process: {str(e)}")
            return "Error during text processing"

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
            print(f"Error retrieving business report (corp_code: {corp_code}): {e}")
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
        """Extract business-related sections from XML content"""
        print("Starting section extraction...")
        soup = BeautifulSoup(xml_content, 'xml')
        
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
        
        print("Searching for section titles...")
        all_titles = soup.find_all(['TITLE', 'SUBTITLE'])
        print(f"Found {len(all_titles)} title elements")
        contents = []
        
        for pattern_type, patterns in business_patterns.items():
            print(f"\nProcessing {pattern_type} patterns...")
            for pattern in patterns:
                for title in all_titles:
                    title_text = title.get_text(strip=True)
                    if re.search(pattern, title_text, re.IGNORECASE):
                        print(f"\nFound section: {title_text}")
                        
                        section_content = []
                        current = title.find_next()
                        safety_counter = 0
                        max_iterations = 1000
                        
                        while current and current.name != 'TITLE' and safety_counter < max_iterations:
                            safety_counter += 1
                            if current.name in ['P', 'TABLE', 'SPAN', 'SUBTITLE']:
                                text = current.get_text(strip=True)
                                if text and len(text) > 5:
                                    if not any(skip in text for skip in ['참고하시기 바랍니다', '참조하시기 바랍니다']):
                                        section_content.append(text)
                                        print(f"Found content: {text[:50]}...")
                            current = current.find_next()
                        
                        if safety_counter >= max_iterations:
                            print("Warning: Maximum iteration limit reached")
                        
                        if section_content:
                            print(f"Processing {len(section_content)} content blocks...")
                            cleaned_content = []
                            for text in section_content:
                                if text not in cleaned_content:
                                    cleaned_content.append(text)
                            
                            contents.extend(cleaned_content)
        
        if not contents:
            print("No business-related sections found")
            return None
        
        return "\n".join(contents)

    def preprocess_text(self, text, company_name):
        """Preprocess text for summarization"""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s.,!?]", "", text)
        text = re.sub(fr"({company_name})\b.*?\b\1", r"\1", text)
        text = re.sub(r"(?i)([A-Za-z]* ?Bonds? -? [0-9A-Za-z ]+|Issuer Credit Rating|채권보다는|원리금 지급능력|기업신용평가)", "", text)
        text = re.sub(r"(?i)(Moodys|S&P|Fitch|한국기업평가|한국신용평가)", "", text)
        text = re.sub(r"(?i)(AAA|AA|A3|BBB|BB|CCC|CC|C|D)([\s-]*안정적|[\s-]*부정적|[\s-]*긍정적)?", "", text)
        return text.strip()

    def chunk_text(self, text, max_tokens=1000):
            """Split text into chunks that won't exceed token limit"""
            sentences = text.split('. ')
            chunks = []
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_tokens = len(self.tokenizer.encode(sentence))
                if current_length + sentence_tokens > max_tokens:
                    if current_chunk:  # 현재 청크가 있으면 저장
                        chunks.append('. '.join(current_chunk) + '.')
                    current_chunk = [sentence]
                    current_length = sentence_tokens
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_tokens
            
            if current_chunk:  # 마지막 청크 저장
                chunks.append('. '.join(current_chunk) + '.')
                
            return chunks

    def clean_text(self, text):
            """Clean text by removing unnecessary patterns and duplicates"""
            # 반복되는 'Lt.' 패턴 제거
            text = re.sub(r'(?:Lt\.,?\s*)+', 'Ltd.', text)
            
            # 반복되는 숫자 패턴 제거
            text = re.sub(r'\b\d+(?:,\d+)*\b(?:\s*\b\d+(?:,\d+)*\b)+', '', text)
            
            # 반복되는 SK 관련 패턴 정리
            text = re.sub(r'SK\s+[Hh]ynix\s+(?:Semiconductor|Semionutor)\s+[A-Za-z]+\s+(?:Ltd\.|Inc\.)', 'SK하이닉스', text)
            
            # 불필요한 약어와 기호 제거
            text = re.sub(r'(?:Co\.,?|Corp\.,?|Inc\.,?)\s*', '', text)
            
            # 중복되는 회사명 정리
            text = re.sub(r'(?:SK하이닉스|에스케이하이닉스)\s*주식회사', 'SK하이닉스', text)
            
            # 연속된 공백 제거
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()

    def remove_duplicate_sentences(self, text):
        """Remove duplicate sentences and similar content"""
        sentences = text.split('. ')
        unique_sentences = []
        seen_content = set()
        
        for sentence in sentences:
            # 문장을 정규화 (공백 제거, 소문자 변환)
            normalized = ' '.join(sentence.lower().split())
            
            # 유사한 문장 감지를 위한 핵심 단어 추출
            words = set(normalized.split())
            
            # 이미 비슷한 내용이 있는지 확인
            is_duplicate = False
            for seen in seen_content:
                common_words = words.intersection(set(seen.split()))
                if len(common_words) > len(words) * 0.6:  # 60% 이상 단어가 겹치면 중복으로 간주
                    is_duplicate = True
                    break
            
            if not is_duplicate and len(normalized) > 10:  # 너무 짧은 문장 제외
                unique_sentences.append(sentence)
                seen_content.add(normalized)
        
        return '. '.join(unique_sentences)

    def remove_duplicate_sentences(self, text):
        """Remove duplicate sentences from summary"""
        sentences = text.split(". ")
        seen = set()
        filtered_sentences = []
        
        for sentence in sentences:
            if sentence not in seen:
                filtered_sentences.append(sentence)
                seen.add(sentence)
        
        return ". ".join(filtered_sentences)

    def get_business_report_content(self, corp_code):
        """Get and process business report content"""
        business_reports = self.get_business_report(corp_code)
        if not business_reports or not business_reports.get("list"):
            print("No business reports found")
            return None
            
        latest_report = business_reports["list"][0]
        rcept_no = latest_report.get("rcept_no")
        print(f"- Found business report: {latest_report.get('rpt_nm')} ({rcept_no})")
        
        xml_content = self.download_report(rcept_no)
        if not xml_content:
            return None
            
        return self.extract_section(xml_content)

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
            # 먼저 기존 문서 검색
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
                # 기존 문서가 있으면 업데이트
                doc_id = hits[0]['_id']
                print(f"Found existing document with ID: {doc_id}")
                response = requests.post(
                    f"{self.es_url}/{self.index_name}/_update/{doc_id}",
                    json={"doc": doc},
                    headers=headers,
                    timeout=30
                )
            else:
                # 새 문서 생성
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

    def process_company(self, company_name, stock_code):
            """Process a single company's data"""
            print(f"\nProcessing {company_name}...")
            
            # Get business report
            corp_code = self.corp_codes.get(stock_code)
            if not corp_code:
                print(f"Could not find corporate code for {company_name}")
                return None
                
            # Get basic company info with corp_code
            company_info = self.get_company_info(company_name, stock_code)
            if not company_info:
                return None
                
            # Get and process business report content
            report_content = self.get_business_report_content(corp_code)
            if not report_content:
                return None
                
            # Summarize content
            summary = self.summarize_text(report_content, company_name)
            
            return {
                "company_name": company_name,
                "company_info": company_info,
                "business_overview": report_content,  # 원문 저장
                "business_overview_summary": summary
            }

    def run(self):
        """Main execution method"""
        try:
            print("Starting business analysis system...")
            
            # Download corporate codes
            self.download_corp_codes()
            
            # Process each company
            results = []
            for company_name, stock_code in self.companies.items():
                company_data = self.process_company(company_name, stock_code)
                if company_data:
                    results.append(company_data)
                    # Upload to Elasticsearch
                    self.upload_to_elasticsearch(company_data)
            
            # Save results to file
            self.save_results(results)
            
            print("\nProcessing completed successfully")
            
        except Exception as e:
            print(f"Error in main execution: {e}")
            raise

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
            company_name = company_data["company_name"]
            file_path = os.path.join(output_dir, f"{company_name}_report.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(company_data, f, ensure_ascii=False, indent=2)
            print(f"Saved individual result for {company_name} to: {file_path}")

def main():
    """Entry point"""
    try:
        system = BusinessAnalysisSystem()
        system.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()