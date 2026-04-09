ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.20
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    libc6-compat \
    libstdc++ \
    libgcc

WORKDIR /app

COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY run.sh /app/run.sh
COPY ptz_service.py /app/ptz_service.py
COPY sdk /app/sdk

RUN chmod a+x /app/run.sh

CMD ["/app/run.sh"]