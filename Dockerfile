# 城市智眼 CityEye —— 一体化镜像：前端构建产物由 FastAPI 同源托管
# 构建：docker build -t cityeye .
# 运行：docker run -p 8000:8000 cityeye   → http://localhost:8000

# ---------- 阶段 1：构建前端 ----------
FROM node:22-alpine AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：运行后端 ----------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY algorithm/cityeye_algo algorithm/cityeye_algo
COPY backend backend
COPY data/geo data/geo
COPY data/samples data/samples
COPY --from=web /app/frontend/dist frontend/dist
EXPOSE 8000
# 数据库、上传文件与算法输出
VOLUME ["/app/backend/var"]
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["python", "-m", "backend", "--host", "0.0.0.0", "--port", "8000"]
