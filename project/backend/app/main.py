from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List, Optional
from app.databases import database, ncs_code   # 데이터베이스 및 테이블 임포트
from app.schema import NCSCode, UserAnswer, InterviewRequest   # Pydantic 모델 임포트
from app.elasticsearch import es_client
from app.ChatGPTService import get_interview_response

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
async def get_ncs_codes(search: Optional[str] = Query(None, description="ncsSubdCdNm 검색어")):
    query = ncs_code.select()
    if search:
        # 대소문자 구분 없이 검색 (ilike)
        query = query.where(ncs_code.c.ncsSubdCdNm.ilike(f"%{search}%"))
    results = await database.fetch_all(query)
    return results

# Elasticsearch 검색 엔드포인트 예제
@app.get("/business_overview", response_model=list)
async def search_elasticsearch(query: str = Query(..., description="검색어 입력")):
    body = {
        "query": {
            "match": {
                "content": query
            }
        }
    }
    try:
        results = es_client.search(index="your_index_name", body=body)
        hits = results.get("hits", {}).get("hits", [])
        return hits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 인터뷰 엔드포인트
@app.post("/interview")
async def interview_endpoint(request: InterviewRequest):
    try:
        print(f"🔹 사용자 입력: {request.answer}, 소분류: {request.subcategory}")
        interview_response = await get_interview_response(request.answer, request.subcategory)
        return {"response": interview_response}
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
