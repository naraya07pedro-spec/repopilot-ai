FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 REPOPILOT_DATA=/data
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml requirements.lock README.md LICENSE ./
COPY repopilot ./repopilot
RUN pip install --no-cache-dir -c requirements.lock ".[postgres]" && useradd --uid 10001 --create-home repopilot && mkdir /data && chown repopilot /data
USER 10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "repopilot.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
