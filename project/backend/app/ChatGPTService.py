import os
import openai
from dotenv import load_dotenv

load_dotenv()  # .env 파일의 환경변수를 로드

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("🚨 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")

# API 키 세팅
openai.api_key = OPENAI_API_KEY

async def get_interview_response(user_answer: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 면접관입니다. 면접 질문을 해주세요."},
                {"role": "user", "content": user_answer}
            ]
        )
    except Exception as e:
        raise Exception(f"Error: {e}")

    # 응답 객체에서 결과 추출 (객체는 dict-like 하게 사용 가능합니다)
    return response["choices"][0]["message"]["content"]