FROM apache/airflow:2.10.4-python3.12

# root 사용자로 필요한 시스템 패키지 설치
USER root
RUN apt-get update && \
    apt-get install -y gosu && \
    apt-get install -y fonts-nanum && \
    # apt-get install -y build-essential default-libmysqlclient-dev openjdk-17-jre pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# airflow 사용자로 변경
USER airflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Airflow 웹 서버 시작
CMD ["airflow", "webserver"]