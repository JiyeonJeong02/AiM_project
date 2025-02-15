import os
import openai
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import pandas as pd
import pymysql
from sqlalchemy import create_engine

load_dotenv()

# 엘라스틱 연결
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', 9200))
es_client = Elasticsearch(
    hosts=[{'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}]
)

# mysql 연결
mysql_user = os.getenv('mysql_user')
mysql_password = os.getenv('mysql_password')
mysql_host = os.getenv('mysql_host')
mysql_port = os.getenv('mysql_port')
connecting_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/NCS_DB"
engine = create_engine(connecting_string)

# LLM 연결
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("🚨 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")

openai.api_key = OPENAI_API_KEY


# 엘라스틱에 답 받아오기
def search_business_overview(company_name):
    # 검색 쿼리 구성: company_name 필드에 대해 입력 받은 값을 매치하고, _source 파라미터로 반환할 필드를 지정합니다.
    body = {
        "query": {
            "match": {
                "company_name": company_name
            }
        },
        "_source": ["business_overview_summary"]
    }

    try:
        results = es_client.search(index="business_overview", body=body)
        hits = results.get("hits", {}).get("hits", [])
        return hits
    except :
        return ""

# 직무내용 받아오기
def create_query(subcategory) :
    query = f"""
    with ncs_code2 as (
    select dutyCd from ncs_code
    where ncsSubdCdNm = '{subcategory}')
    select gbnName, gbnVal
    from ncs_code2 c, ncs_skills s
    where c.dutyCd = s.dutyCd;
    """
    return query
def execute_query_to_dataframe(query):
    try:
        # pandas의 read_sql 함수를 사용하여 쿼리 실행 및 DataFrame 생성
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Error executing query: {e}")
        return None


async def get_interview_response(user_answer: str, companyname: str, subcategory: str) -> str:
    try:
        # 기업정보 받아오기
        business_overview = search_business_overview(companyname)
        ncs_skills = execute_query_to_dataframe(create_query(subcategory))
        print(ncs_skills)

        prompt = f"""
        [기업 정보]
        {business_overview}

        [지원 직무]
        {subcategory}

        [직무 역량]
        {ncs_skills}
        

        당신은 {companyname}의 면접관입니다.

        지원자가 자기소개한 것을 토대로, 다음 요구사항을 모두 반영하여 후속 질문(꼬리 질문)을 생성하십시오:
        1. 기업의 사업 특성을 반영한 질문  
        2. 해당 직무에서 요구되는 역량을 평가할 수 있는 질문  
        3. 상황판단 능력을 평가하는 질문  
        4. 앞서 지원자가 제출한 자기소개를 기반으로 한 추가 질문

        반드시 한 번에 하나의 질문만 생성해 주세요.

        지원자 자기소개:
        "{user_answer}"
        """

        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",  # 최신 GPT 모델 사용
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_answer}
            ]
        )
        return response["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        print(f"❌ OpenAI API 오류 발생: {e}")
        return "죄송합니다. 응답을 생성하는 중 오류가 발생했습니다."
    


async def get_interview_feedback(conversation_text: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 전문 면접관입니다. 다음 대화 내용을 바탕으로 면접 피드백(요약)을 제공하세요. "
                        "개선할 점을 간략하게 정리해 주세요."
                    )
                },
                {"role": "user", "content": conversation_text}
            ]
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ 피드백 생성 오류 발생: {e}")
        return "죄송합니다. 피드백을 생성하는 중 오류가 발생했습니다."