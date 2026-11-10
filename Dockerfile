FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# Numeric UID on purpose: Kubernetes can only enforce runAsNonRoot when the
# image's user is a number, not a name like "appuser".
RUN useradd --create-home --uid 10001 appuser
USER 10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
