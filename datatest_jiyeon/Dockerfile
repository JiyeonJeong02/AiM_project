FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install tf-keras

COPY . .

CMD ["python", "big5_bus_info_summary.py"]
