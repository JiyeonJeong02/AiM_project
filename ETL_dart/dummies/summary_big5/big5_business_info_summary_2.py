import os
import json
import re
import requests
from transformers import pipeline, AutoTokenizer
from dotenv import load_dotenv

# ✅ .env 파일 로드
load_dotenv()

# ✅ 환경 변수 가져오기
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
KIBANA_URL = os.getenv("KIBANA_URL")
INDEX_NAME = os.getenv("INDEX_NAME", "business_overview")

# ✅ KoBART 모델 설정
model_name = "digit82/kobart-summarization"
tokenizer = AutoTokenizer.from_pretrained(model_name)
summarizer = pipeline("summarization", model=model_name, tokenizer=tokenizer)

# ✅ JSON 파일 경로 (기업 보고서 원본 파일)
JSON_FILE_PATH = "output/company_reports.json"

def remove_financial_info(text):
    """재무 정보, 신용등급 관련 정보 제거 (연도/날짜는 유지)"""
    text = re.sub(r"(?i)([A-Za-z]* ?Bonds? -? [0-9A-Za-z ]+|Issuer Credit Rating|채권보다는|원리금 지급능력|기업신용평가)", "", text)
    text = re.sub(r"(?i)(Moodys|S&P|Fitch|한국기업평가|한국신용평가)", "", text)  # 신용등급 기관 제거
    text = re.sub(r"(?i)(AAA|AA|A3|BBB|BB|CCC|CC|C|D)([\s-]*안정적|[\s-]*부정적|[\s-]*긍정적)?", "", text)  # 신용등급 제거
    text = re.sub(r"\(주\d+\)", "", text)  # "(주1)" 같은 주석 제거
    text = re.sub(r"\s+", " ", text).strip()  # 연속된 공백 제거
    return text

def remove_redundant_words(text):
    """반복되는 기업명 접미어 (Ltd., Inc., Co., LLC., 등) 제거"""
    redundant_patterns = [
        r"\bLtd\.,?", r"\bInc\.,?", r"\bCo\.,?", r"\bLLC\.,?",
        r"\bGmbH\.,?", r"\bCorp\.,?", r"\bPLC\.,?", r"\bLimited\.,?"
    ]

    for pattern in redundant_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)  # 대소문자 구분 없이 제거

    # ✅ 연속된 중복 단어 제거 (예: "Ltd. Ltd. Ltd." → "Ltd.")
    text = re.sub(r"\b(\w+)( \1)+\b", r"\1", text)

    text = re.sub(r"\s+", " ", text).strip()  # ✅ 불필요한 공백 제거
    return text

def preprocess_text(text, company_name):
    """회사명 한 번 유지 + 기업명 접미어 제거 + 재무 정보 제거"""
    text = re.sub(r"\s+", " ", text)  # 연속된 공백 제거
    text = re.sub(r"[^\w\s.,!?]", "", text)  # 특수문자 제거

    # ✅ 회사명이 여러 번 반복될 경우, 첫 번째 등장 이후 삭제
    text = re.sub(fr"({company_name})\b.*?\b\1", r"\1", text)

    # ✅ 기업명 접미어 제거 (Ltd., Inc., 등)
    text = remove_redundant_words(text)

    # ✅ 불필요한 재무 정보 제거 (연도/날짜는 유지)
    text = remove_financial_info(text)

    return text.strip()

def remove_duplicate_sentences(text):
    """요약된 문장에서 중복된 문장을 제거"""
    sentences = text.split(". ")
    seen = set()
    filtered_sentences = []

    for sentence in sentences:
        if sentence not in seen:
            filtered_sentences.append(sentence)
            seen.add(sentence)

    return ". ".join(filtered_sentences)

def summarize_text(text_chunks, company_name):
    """각각의 텍스트 조각을 요약한 후, 최종 요약"""
    summaries = []
    
    for chunk in text_chunks:
        chunk = preprocess_text(chunk, company_name)  # ✅ 전처리 적용
        input_length = len(tokenizer.encode(chunk, add_special_tokens=False))
        max_length = min(700, max(100, input_length // 2))

        try:
            summary = summarizer(chunk, max_length=max_length, min_length=50, do_sample=False)
            result = summary[0]["summary_text"]

            # ✅ 비정상적인 요약 감지 후 재처리
            if len(set(result.split())) < 5:  
                print("⚠ 비정상적인 요약 감지, 다시 요약 시도...")
                result = summarizer(chunk, max_length=max(200, input_length // 3), min_length=50, do_sample=True)[0]["summary_text"]
            
            summaries.append(result)
        except Exception as e:
            print(f"❌ 요약 중 오류 발생: {e}")
            summaries.append("요약 실패")

    # ✅ 전체 요약 조각을 다시 하나의 요약으로 처리
    combined_summary = " ".join(summaries)
    combined_summary = remove_duplicate_sentences(combined_summary)  # ✅ 중복 문장 제거

    if len(tokenizer.encode(combined_summary, add_special_tokens=False)) > 1024:
        try:
            final_summary = summarizer(combined_summary, max_length=700, min_length=100, do_sample=False)
            return remove_duplicate_sentences(final_summary[0]["summary_text"])  # ✅ 최종 요약에서도 중복 제거
        except Exception as e:
            print(f"❌ 최종 요약 중 오류 발생: {e}")
            return combined_summary  # 최종 요약 실패 시, 부분 요약 결과 반환
    
    return combined_summary

def load_json_data(file_path):
    """ JSON 파일을 로드하여 리스트로 반환 """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for company in data:
        company_name = company.get("company_name", "Unknown")
        business_overview = company.get("business_overview", "")

        if not business_overview:
            print(f"⚠ {company_name}의 사업 개요 없음, 건너뜀.")
            continue

        text_chunks = [business_overview]  
        summarized_text = summarize_text(text_chunks, company_name)

        company["business_overview_summary"] = summarized_text

    return data

def upload_to_elasticsearch(data):
    """Elasticsearch에 데이터 업로드 (업데이트 또는 삽입)"""
    headers = {"Content-Type": "application/json"}

    for company in data:
        company_name = company.get("company_name")
        business_overview_summary = company.get("business_overview_summary", "")

        if not business_overview_summary:
            print(f"⚠ {company_name}의 요약 데이터가 없습니다. 건너뜀.")
            continue

        update_url = f"{ELASTICSEARCH_URL}/{INDEX_NAME}/_update_by_query"
        update_query = {
            "script": {
                "source": "ctx._source.business_overview_summary = params.summary",
                "params": {"summary": business_overview_summary}
            },
            "query": {
                "match": {
                    "company_name": company_name
                }
            }
        }
        response = requests.post(update_url, headers=headers, json=update_query)

        if response.status_code == 200:
            print(f"🔄 {company_name} 데이터 업데이트 완료!")
        else:
            print(f"❌ {company_name} 데이터 업데이트 실패! {response.text}")

if __name__ == "__main__":
    json_data = load_json_data(JSON_FILE_PATH)
    upload_to_elasticsearch(json_data)
