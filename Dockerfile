FROM python:3.14-slim AS base

FROM base as builder

RUN python -m pip install --no-cache-dir -U pip wheel

COPY ./requirements.txt /tmp/

RUN python -OO -m pip wheel --no-cache-dir --wheel-dir=/tmp/wheels -r /tmp/requirements.txt 

FROM base

COPY --from=builder /tmp/wheels /tmp/wheels

ADD ./src /app/src
ADD ./config.env /app/config.env

WORKDIR /app/src

RUN python -m pip install --no-cache --no-index /tmp/wheels/* && \
    rm -rf /tmp/wheels

ENV APP_RUN_MODE=PROD
ENTRYPOINT [ "python" ]
CMD [ "-OO", "-B" ,"main.py" ]