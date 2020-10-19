FROM python:3.8.0-slim-buster

WORKDIR /app

COPY requirements.txt /app/

RUN apt update && \
    apt install -y gcc

RUN pip install --upgrade pip

RUN head -n 1 requirements.txt | pip install -r /dev/stdin  # Installs Cython

RUN pip install -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

ENV PYTHONPATH "${PYTHONPATH}:/app"

CMD ["python", "fairtracks_augment/app.py"]
