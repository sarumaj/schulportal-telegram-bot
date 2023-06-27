FROM python:3.10

RUN pip install ./requirements.txt

RUN mkdir /app
ADD . /app
WORKDIR /app

CMD python /app/main.py 