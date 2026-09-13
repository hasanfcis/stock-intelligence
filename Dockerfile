FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal — pure-Python stack.
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir ".[live]"

# The scheduler entrypoint runs the pipeline once a day and, if configured,
# delivers to Telegram. See docker-compose.yml for the cron-style trigger.
ENTRYPOINT ["python", "-m", "stock_intel.cli"]
CMD ["run", "--live", "--telegram", "--out", "/app/data/daily_report.json"]
