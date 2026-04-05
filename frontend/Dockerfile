# 1단계: 무거운 Node.js 환경에서 리액트 코드 압축(Build)하기
FROM node:18-alpine as builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# 2단계: 가벼운 Nginx 환경으로 갈아타서 압축된 파일만 서빙하기
FROM nginx:alpine
# 1단계(builder)에서 완성된 결과물(/app/build)만 Nginx 서빙 폴더로 쏙 빼옵니다.
COPY --from=builder /app/build /usr/share/nginx/html

COPY default.conf /etc/nginx/conf.d/default.conf

# Nginx 기본 포트는 80입니다.
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]