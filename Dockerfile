FROM python:3.8.0-slim-buster

WORKDIR /fairtracks-augment

COPY requirements.txt /fairtracks-augment/

RUN apt update && \
    apt install -y gcc

RUN pip install --upgrade pip

RUN head -n 1 requirements.txt | pip install -r /dev/stdin  # Installs Cython

RUN pip install -r requirements.txt

COPY . /fairtracks-augment

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
