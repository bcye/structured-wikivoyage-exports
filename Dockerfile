FROM ghcr.io/astral-sh/uv:0.6-python3.12-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "main.py"]