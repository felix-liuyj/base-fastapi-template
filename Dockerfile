FROM python:3.11

WORKDIR /code
COPY . .

# It's required that the Pipfile.lock presents in the current folder for the option to work.--system
RUN pip3 install pipenv && pipenv lock && pipenv install --deploy --system

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]