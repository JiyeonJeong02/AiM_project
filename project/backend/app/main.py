from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .ChatGPTService import get_interview_response

app = FastAPI()

class UserAnswer(BaseModel):
    answer: str

# ✅ CORS 설정 (모든 도메인 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/interview")
async def interview_endpoint(user: UserAnswer):
    try:
        print(f"🔹 사용자 입력: {user.answer}")  # ✅ 디버깅 로그 추가
        interview_response = await get_interview_response(user.answer)
        return {"response": interview_response}
    except Exception as e:
        print(f"❌ 서버 오류: {e}")  # ✅ FastAPI 로그 기록
        raise HTTPException(status_code=500, detail=str(e))
