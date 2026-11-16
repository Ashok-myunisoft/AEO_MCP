FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_SERVER_HOST=0.0.0.0 \
    MCP_SERVER_PORT=8071

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p storage/uploads storage/extracted logs \
    && chown -R app:app /app

USER app

EXPOSE 8071

CMD ["python", "-m", "app.mcp_server.server"]
