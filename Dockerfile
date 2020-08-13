FROM python:3.8.0-slim-buster

WORKDIR /fairtracks-augment

COPY ./ /fairtracks-augment/

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
