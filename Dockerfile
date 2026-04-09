ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache \
    python3 \
    py3-flask \
    bash \
    libc6-compat \
    libstdc++ \
    libgcc

WORKDIR /app

COPY run.sh /app/run.sh
COPY ptz_service.py /app/ptz_service.py
COPY sdk /app/sdk

RUN chmod a+x /app/run.sh

CMD ["/app/run.sh"]