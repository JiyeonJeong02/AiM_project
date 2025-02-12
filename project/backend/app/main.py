from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import databases
import sqlalchemy
from app.ChatGPTService import get_interview_response  # 기존 모듈 임포트

# 데이터베이스 연결 (예: MySQL, PostgreSQL 등)
DATABASE_URL = "mysql://ims:imsgreat1!W@221.155.195.6:3306/NCS_DB"  # 실제 환경에 맞게 수정
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# NCS 코드 테이블 정의 (컬럼 이름은 실제 스키마와 일치해야 함)
ncs_code = sqlalchemy.Table(
    "ncs_code",
    metadata,
    sqlalchemy.Column("ncsDegr", sqlalchemy.String),
    sqlalchemy.Column("ncsLclasCd", sqlalchemy.String),
    sqlalchemy.Column("ncsLclasCdNm", sqlalchemy.String),
    sqlalchemy.Column("ncsMclasCd", sqlalchemy.String),
    sqlalchemy.Column("ncsMclasCdNm", sqlalchemy.String),
    sqlalchemy.Column("ncsSclasCd", sqlalchemy.String),
    sqlalchemy.Column("ncsSclasCdNm", sqlalchemy.String),
    sqlalchemy.Column("ncsSubdCd", sqlalchemy.String),
    sqlalchemy.Column("ncsSubdCdNm", sqlalchemy.String),
    sqlalchemy.Column("dutyCd", sqlalchemy.String)
)

# Pydantic 모델 (응답 모델)
class NCSCode(BaseModel):
    ncsDegr: Optional[str]
    ncsLclasCd: Optional[str]
    ncsLclasCdNm: Optional[str]
    ncsMclasCd: Optional[str]
    ncsMclasCdNm: Optional[str]
    ncsSclasCd: Optional[str]
    ncsSclasCdNm: Optional[str]
    ncsSubdCd: Optional[str]
    ncsSubdCdNm: Optional[str]
    dutyCd: Optional[str]

class UserAnswer(BaseModel):
    answer: str

app = FastAPI()

# CORS 설정 (모든 도메인 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 앱 시작/종료 이벤트에서 데이터베이스 연결/해제
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# NCS 코드 검색 엔드포인트
@app.get("/api/ncs-codes", response_model=List[NCSCode])
async def get_ncs_codes(search: Optional[str] = Query(None, description="ncsLclasCdNm 검색어")):
    query = ncs_code.select()
    if search:
        # 대소문자 구분 없이 검색 (ilike)
        query = query.where(ncs_code.c.ncsLclasCdNm.ilike(f"%{search}%"))
    results = await database.fetch_all(query)
    return results

# 인터뷰 엔드포인트 (기존 코드)
@app.post("/interview")
async def interview_endpoint(user: UserAnswer):
    try:
        print(f"🔹 사용자 입력: {user.answer}")
        interview_response = await get_interview_response(user.answer)
        return {"response": interview_response}
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
