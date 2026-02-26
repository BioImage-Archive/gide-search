# Define base image (Python 3.13 + uv pre-installed)
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

EXPOSE 8000

ADD . /app
WORKDIR /app

RUN uv lock
RUN uv sync

CMD ["uv", "run", "gide-search", "serve", "--host", "0.0.0.0", "--port", "8000"]