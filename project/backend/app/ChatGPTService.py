import os
import openai
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

# 엘라스틱 연결
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', 9200))

es_client = Elasticsearch(
    hosts=[{'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}]
)

# LLM 연결
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("🚨 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")

openai.api_key = OPENAI_API_KEY


# 엘라스틱에 답 받아오기


# 직무내용 받아오기





async def get_interview_response(user_answer: str, companyname : str, subcategory: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",  # 최신 GPT 모델 사용
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"당신은 전문 면접관입니다. 사용자가 선택한 직무 '{subcategory}' "
                        "에 관련된 면접 질문을 준비하세요. 해당 분야의 핵심 역량과 관련된 질문을 해주세요."
                        "질문은 한 문장씩만 해주세요"
                    )
                },
                {"role": "user", "content": user_answer}
            ]
        )
        return response["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        print(f"❌ OpenAI API 오류 발생: {e}")
        return "죄송합니다. 응답을 생성하는 중 오류가 발생했습니다."