# ---- Build stage ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY client/package.json client/pnpm-lock.yaml ./
# 安装 pnpm
RUN npm install -g pnpm
RUN pnpm install

COPY client ./
RUN pnpm run build

# ---- Production stage ----
FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# 拷贝构建产物
COPY --from=builder /app/dist ./

# 配置 nginx（可选：自定义 nginx.conf）
# COPY client/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]