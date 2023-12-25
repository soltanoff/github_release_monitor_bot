FROM python:3.12-slim
ENV PYTHONUNBUFFERED 0

RUN apt-get update \
    && pip install --upgrade --no-cache-dir pip \
    && pip install --upgrade --no-cache-dir wheel \
    && pip install --upgrade --no-cache-dir setuptools \
    && pip install --upgrade --no-cache-dir poetry

WORKDIR /app

# will be cached if no changes in this files
COPY poetry.lock /app/
COPY pyproject.toml /app/

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction

COPY .. /app

CMD [ "python", "main.py" ]