import os
import openai
from dotenv import load_dotenv

# ✅ .env 파일에서 환경 변수 로드
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("🚨 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")

# ✅ API 키 설정
openai.api_key = OPENAI_API_KEY

async def get_interview_response(user_answer: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",  # ✅ 최신 GPT 모델 사용
            messages=[
                {"role": "system", "content": "당신은 면접관입니다. 면접 질문을 해주세요."},
                {"role": "user", "content": user_answer}
            ]
        )
        return response["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        print(f"❌ OpenAI API 오류 발생: {e}")  # ✅ 서버 로그 기록
        return "죄송합니다. 응답을 생성하는 중 오류가 발생했습니다."
