import os
from elasticsearch import Elasticsearch

# 환경변수 또는 기본값으로 ES 정보 설정
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST')
ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT'))

# Elasticsearch 클라이언트 인스턴스 생성
es_client = Elasticsearch(
    hosts=[{'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'}]
)