.PHONY: help install test lint run docker clean

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	pip install -e ".[dev]"

test:  ## 运行测试
	python -m pytest tests/ -v --timeout=30

test-cov:  ## 运行测试并生成覆盖率报告
	python -m pytest tests/ -v --timeout=30 --cov=providers --cov-report=term-missing

run:  ## 启动 API 服务
	python server.py

run-external:  ## 启动 API 服务 (允许外部访问)
	python server.py --host 0.0.0.0

demo:  ## 运行端到端测试
	python examples/demo_all.py

docker-build:  ## 构建 Docker 镜像
	docker build -t chatgptmail-2api .

docker-run:  ## 运行 Docker 容器
	docker run -p 8787:8787 chatgptmail-2api

docker-up:  ## Docker Compose 启动
	docker compose up -d

docker-down:  ## Docker Compose 停止
	docker compose down

clean:  ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
