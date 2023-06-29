FROM python:3.10

RUN mkdir /app
ADD . /app
WORKDIR /app

RUN pip install --upgrade pip && pip install -r /app/requirements.txt

CMD APP_RUN_MODE=PROD python /app/src/main.py