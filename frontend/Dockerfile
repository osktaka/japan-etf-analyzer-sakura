FROM node:20-alpine

WORKDIR /app

# 依存関係インストール
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
