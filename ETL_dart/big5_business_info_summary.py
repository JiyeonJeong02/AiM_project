import os
import json
import re
from transformers import pipeline, AutoTokenizer

# JSON 파일이 저장된 디렉토리
OUTPUT_DIR = "output"

# ✅ KoBART 모델 설정 (최대 1024 토큰)
model_name = "digit82/kobart-summarization"
tokenizer = AutoTokenizer.from_pretrained(model_name)
summarizer = pipeline("summarization", model=model_name, tokenizer=tokenizer)

def clean_text(text):
    """텍스트 전처리: 특수문자, 공백, HTML 태그 제거"""
    text = re.sub(r"<[^>]+>", "", text)  # HTML 태그 제거
    text = re.sub(r"\s+", " ", text)  # 연속 공백 제거
    text = re.sub(r"[^가-힣a-zA-Z0-9.,?!%()\- ]", "", text)  # 한글, 영어, 숫자, 기본 문장부호 유지
    return text.strip()

def chunk_text(text, max_tokens=512):
    """텍스트를 문장 단위로 나누어 모델이 처리할 수 있도록 정리"""
    sentences = re.split(r"(?<=[.?!])\s+", text)  # 문장 단위로 분할
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(tokenizer.encode(current_chunk + sentence, add_special_tokens=False)) < max_tokens:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def is_valid_summary(summary):
    """비정상적인 요약 감지 (너무 짧거나 의미 없는 문장)"""
    if len(summary) < 10:  # 너무 짧은 경우
        return False
    if len(set(summary.split())) < 5:  # 너무 적은 단어만 포함된 경우
        return False
    return True

def summarize_text(text_chunks):
    """여러 개의 텍스트 조각을 각각 요약한 후 최종 요약"""
    summaries = []
    
    for chunk in text_chunks:
        input_length = len(tokenizer.encode(chunk, add_special_tokens=False))
        max_length = min(512, max(50, input_length // 2))  # ✅ max_length 자동 조정

        try:
            summary = summarizer(chunk, max_length=max_length, min_length=30, do_sample=False)
            result = summary[0]["summary_text"]
            
            # ✅ 비정상적인 요약 감지 후 재처리
            if not is_valid_summary(result):
                print("⚠ 비정상적인 요약 감지, 다시 요약 시도...")
                result = summarizer(chunk, max_length=max(100, input_length // 3), min_length=30, do_sample=True)[0]["summary_text"]
            
            summaries.append(result)
        except Exception as e:
            print(f"❌ 요약 중 오류 발생: {e}")
            summaries.append("요약 실패")
    
    # 최종 요약 (조각들을 다시 요약)
    combined_summary = " ".join(summaries)

    # ✅ 최종 요약이 너무 길 경우 다시 한번 요약
    if len(tokenizer.encode(combined_summary, add_special_tokens=False)) > 1024:
        try:
            final_summary = summarizer(combined_summary, max_length=512, min_length=100, do_sample=False)
            return final_summary[0]["summary_text"]
        except Exception as e:
            print(f"❌ 최종 요약 중 오류 발생: {e}")
            return combined_summary  # 최종 요약 실패 시, 부분 요약 결과 반환
    
    return combined_summary

def process_summaries(company_data):
    """각 기업의 business_overview를 요약하고 새로운 JSON 저장"""
    summary_results = []

    for company in company_data:
        company_name = company["company_name"]
        business_overview = company.get("business_overview", "")

        if not business_overview:
            print(f"⚠ {company_name}의 business_overview가 없습니다. 원본 데이터를 확인하세요.")
            continue  # business_overview가 없으면 건너뜀

        print(f"▶ {company_name} 사업 개요 요약 중... (원본 길이: {len(business_overview)}자)")

        # ✅ 전처리 적용
        business_overview = clean_text(business_overview)

        # ✅ 1024 토큰 초과 시 문장 단위로 분할하여 요약
        text_chunks = chunk_text(business_overview)
        summary = summarize_text(text_chunks)
        
        company["business_overview_summary"] = summary
        summary_results.append(company)

    return summary_results

def save_summaries(summary_results, output_dir="output"):
    """요약된 내용을 새로운 JSON 파일로 저장"""
    summary_file = os.path.join(output_dir, "company_reports_summarized.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 요약된 결과 저장 완료: {summary_file}")

def load_json_files(output_dir):
    """output 디렉토리 내 모든 JSON 파일을 불러와 리스트로 반환"""
    company_data = []
    for filename in os.listdir(output_dir):
        if filename.endswith("_report.json"):  # 기업별 개별 보고서만 처리
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                company_data.append(data)
    
    if not company_data:
        raise ValueError("❌ output 폴더에 JSON 파일이 없습니다. big5.py를 실행하여 데이터를 생성하세요.")

    return company_data

# 실행
if __name__ == "__main__":
    company_data = load_json_files(OUTPUT_DIR)
    summarized_data = process_summaries(company_data)
    save_summaries(summarized_data)
