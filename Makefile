# 城市智眼 CityEye 常用命令
PY ?= python3

.PHONY: help install dev demo build test snapshot geo samples docker clean

help:  ## 显示帮助
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  \033[36mmake %-9s\033[0m %s\n", $$1, $$2}'

install:  ## 安装前后端依赖
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm ci --no-audit --no-fund

dev:  ## 开发模式（后端 :8000 热重载 + 前端 :5173）
	PYTHON=$(PY) ./scripts/dev.sh

demo:  ## 演示模式（构建前端，单端口 :8000）
	PYTHON=$(PY) ./scripts/demo.sh

build:  ## 构建前端
	cd frontend && npm run build

test:  ## 运行算法与后端测试
	$(PY) -m pytest algorithm/tests -q
	cd backend && $(PY) -m pytest tests -q

snapshot:  ## 从后端导出前端离线快照（frontend/public/snapshot）
	$(PY) scripts/export_snapshot.py

geo:  ## 重新抓取并加工 OpenStreetMap 城市底座
	$(PY) data/scripts/fetch_osm.py --out data/raw/osm
	$(PY) data/scripts/build_geo.py --raw data/raw/osm --out data/geo

samples:  ## 重新生成合成演示样本
	$(PY) data/scripts/generate_samples.py

docker:  ## Docker 一键运行
	docker compose up --build

clean:  ## 清理运行时数据与构建产物
	rm -rf backend/var frontend/dist
	find . -name __pycache__ -type d -prune -not -path "./frontend/node_modules/*" -exec rm -rf {} +
