# use python 3.12 as a base image
FROM docker.io/python:3.12-alpine
# use the latest version of uv, independently of the python version
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# copy the requirements and install them
COPY pyproject.toml uv.lock .
RUN uv sync --frozen

# copy the rest of the code
COPY src .

CMD ["uv", "run", "main.py"]
