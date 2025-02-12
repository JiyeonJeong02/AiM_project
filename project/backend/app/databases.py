import os
import sqlalchemy
import pymysql
import databases


mysql_user = os.getenv('mysql_user')
mysql_password= os.getenv('mysql_password')
mysql_host = os.getenv('mysql_host')
mysql_port = os.getenv('mysql_port')


# 데이터베이스 연결
DATABASE_URL = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/NCS_DB"
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

