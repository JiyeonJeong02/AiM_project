from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import zipfile
import os
from io import BytesIO
from bs4 import BeautifulSoup
import pymysql
import pandas as pd
from dotenv import load_dotenv
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 데이터베이스 설정
DB_CONFIG = {
    'host': os.getenv('host'),
    'user': os.getenv('USER'),
    'password': os.getenv('PASWD'),
    'port': int(os.getenv('port')),
    'database': os.getenv('DB_NAME', 'DART_DB')  # DB_NAME이 없을 경우에만 기본값 사용
}

def create_table():
    """테이블 생성 함수"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_overviews (
                    corp_code VARCHAR(8) PRIMARY KEY,
                    corp_name VARCHAR(100),
                    stock_code VARCHAR(6),
                    overview TEXT,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
        conn.commit()
        logger.info("Table created successfully")
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise
    finally:
        conn.close()

def get_company_list():
    """DART에서 기업 목록 가져오기"""
    api_key = os.getenv('DART_API_KEY')
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    
    response = requests.get(url, params={'crtfc_key': api_key})
    if response.status_code != 200:
        raise Exception(f"Failed to get company list: {response.status_code}")
    
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        with z.open(z.namelist()[0]) as f:
            soup = BeautifulSoup(f, 'xml')
    
    companies = []
    for corp in soup.find_all('list'):
        stock_code = corp.find('stock_code').text.strip()
        if stock_code:  # 상장 기업만 포함
            companies.append({
                'corp_code': corp.find('corp_code').text.strip(),
                'corp_name': corp.find('corp_name').text.strip(),
                'stock_code': stock_code
            })
    
    logger.info(f"Retrieved {len(companies)} listed companies")
    return companies

def extract_company_overview(xml_content):
    """XML에서 회사 개요 추출"""
    soup = BeautifulSoup(xml_content, 'xml')
    section = soup.find("TITLE", string=lambda text: text and "회사의 개요" in text)
    
    if not section:
        return None
    
    content = []
    for sibling in section.find_all_next():
        if sibling.name == "TITLE":
            break
        if sibling.name in ["P", "TABLE", "SPAN"]:
            text = sibling.get_text(strip=True)
            if text and text not in content:
                content.append(text)
    
    return "\n".join(content) if content else None

def get_processed_corp_codes():
    """MySQL에서 이미 처리된 기업 목록 조회"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT corp_code FROM company_overviews")
            processed_corp_codes = {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()
    return processed_corp_codes

def process_company_batch(**context):
    """기업 배치 처리 (이미 처리된 기업 제외)"""
    api_key = os.getenv('DART_API_KEY')
    task_instance = context['task_instance']
    companies = task_instance.xcom_pull(task_ids='get_company_list')

    # ✅ MySQL에서 이미 처리된 기업 조회
    processed_corp_codes = get_processed_corp_codes()

    new_companies = [company for company in companies if company['corp_code'] not in processed_corp_codes]

    if not new_companies:
        logger.info("No new companies to process.")
        return

    # ✅ MySQL 연결을 전체 로직에서 관리
    conn = pymysql.connect(**DB_CONFIG)
    try:
        cursor = conn.cursor()
        for company in new_companies:
            try:
                url = "https://opendart.fss.or.kr/api/list.json"
                params = {
                    'crtfc_key': api_key,
                    'corp_code': company['corp_code'],
                    'pblntf_ty': 'A',  
                    'page_count': 1,
                    'pblntf_detail_ty': ['A001', 'A002', 'A003', 'A004']
                }
                response = requests.get(url, params=params)
                if response.status_code != 200 or not response.json().get('list'):
                    logger.warning(f"No reports found for {company['corp_name']}")
                    continue

                rcept_no = response.json()['list'][0]['rcept_no']

                doc_url = "https://opendart.fss.or.kr/api/document.xml"
                doc_params = {'crtfc_key': api_key, 'rcept_no': rcept_no}
                doc_response = requests.get(doc_url, params=doc_params)
                if doc_response.status_code != 200:
                    logger.warning(f"Failed to get document for {company['corp_name']}")
                    continue

                with zipfile.ZipFile(BytesIO(doc_response.content)) as z:
                    xml_content = z.read(z.namelist()[0]).decode('utf-8')

                overview = extract_company_overview(xml_content)
                if overview:
                    cursor.execute("""
                        INSERT INTO company_overviews 
                        (corp_code, corp_name, stock_code, overview)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE overview=VALUES(overview), updated_at=CURRENT_TIMESTAMP
                    """, (company['corp_code'], company['corp_name'], company['stock_code'], overview))
                    logger.info(f"Successfully processed {company['corp_name']}")

            except Exception as e:
                logger.error(f"Error processing company {company['corp_name']}: {str(e)}")
                continue  # ✅ 오류 발생 시 다음 기업으로 계속 진행

        conn.commit()  # ✅ 모든 데이터를 처리한 후 한 번만 `commit()`
    
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
    
    finally:
        conn.close()  # ✅ MySQL 연결은 최종적으로 닫기

    logger.info(f"Successfully processed batch of {len(new_companies)} new companies")



# DAG 정의
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 2, 7),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'dart_company_overview_etl',
    default_args=default_args,
    description='ETL DAG for company overviews from DART',
    schedule_interval='0 1 * * *',  # 매일 새벽 1시
    catchup=False
)

create_table_task = PythonOperator(
    task_id='create_table',
    python_callable=create_table,
    dag=dag,
)

get_companies_task = PythonOperator(
    task_id='get_company_list',
    python_callable=get_company_list,
    dag=dag,
)

process_companies_task = PythonOperator(
    task_id='process_companies',
    python_callable=process_company_batch,
    provide_context=True,
    dag=dag,
)

# 태스크 순서 설정
create_table_task >> get_companies_task >> process_companies_task