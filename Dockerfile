FROM python:3

WORKDIR /fairtracks-autogenerate

COPY ./ /fairtracks-autogenerate/

RUN pip install -r requirements.txt

CMD ["python", "app.py"]