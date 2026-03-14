FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir akshare anthropic jinja2 pydantic python-dotenv openai

# 项目代码
COPY config/ config/
COPY src/ src/
COPY prompts/ prompts/
COPY main.py .

# 运行时目录
RUN mkdir -p state/cache reports/daily

ENTRYPOINT ["python", "main.py"]
CMD ["--date", "20260313"]
