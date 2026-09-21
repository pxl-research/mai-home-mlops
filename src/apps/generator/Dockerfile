FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py detector.py .
COPY models/ ./models/
CMD ["python", "main.py"]
