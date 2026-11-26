FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8765

WORKDIR /app
COPY --chmod=444 server.py index.html ./
USER 10001:10001
EXPOSE 8765
CMD ["python3", "server.py"]
