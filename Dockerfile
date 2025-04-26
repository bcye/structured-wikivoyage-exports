FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "transform-documents.py"]