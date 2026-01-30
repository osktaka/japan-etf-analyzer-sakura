FROM python:3.9-slim

WORKDIR /app

# 依存関係インストール
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

ENV FLASK_APP=src/app.py
ENV FLASK_ENV=development

EXPOSE 8902

CMD ["flask", "run", "--host=0.0.0.0", "--port=8902"]
