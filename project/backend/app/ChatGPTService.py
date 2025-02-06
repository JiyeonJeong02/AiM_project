import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # .env 파일의 환경변수를 로드

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("🚨 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")

openai = OpenAI(api_key=OPENAI_API_KEY)

async def get_interview_response(user_answer: str) -> str:
    try:
        response = await openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 면접관입니다. 면접 질문을 해주세요."},
                {"role": "user", "content": user_answer}
            ]
        )
    except Exception as e:
        raise Exception(f"Error: {e}")

    return response.choices[0].message.content
