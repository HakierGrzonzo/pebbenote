FROM python:3.13
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
EXPOSE 80

RUN python3 -m pip install poetry
WORKDIR /app
COPY ./poetry.lock ./pyproject.toml ./
RUN poetry config virtualenvs.in-project true --local
RUN poetry install --no-root
COPY . .
ENTRYPOINT poetry run uvicorn pebbenote:app --host 0.0.0.0 --port 80 --proxy-headers

