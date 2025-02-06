from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .ChatGPTService import get_interview_response

app = FastAPI()

class UserAnswer(BaseModel):
    answer: str

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (보안상 필요 시 제한)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

@app.post("/interview")
async def interview_endpoint(user: UserAnswer):
    try:
        interview_response = await get_interview_response(user.answer)
        return {"response": interview_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))