import os
import sqlalchemy
import databases

# 환경 변수 또는 기본값 사용 (예시)
mysql_user = os.getenv('mysql_user', 'your_username')
mysql_password = os.getenv('mysql_password', 'your_password')
mysql_host = os.getenv('mysql_host', 'localhost')
mysql_port = os.getenv('mysql_port', '3306')

DATABASE_URL = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/NCS_DB"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# NCS 코드 테이블 정의
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
