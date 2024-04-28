FROM PROJECT_NAME-runtime:latest

WORKDIR /code

COPY . /code

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]