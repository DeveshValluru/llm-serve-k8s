FROM python:3.11-slim
RUN pip install --no-cache-dir fastapi uvicorn transformers torch --extra-index-url https://download.pytorch.org/whl/cpu
WORKDIR /srv
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]