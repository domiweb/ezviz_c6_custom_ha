ARG BUILD_ARCH
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base-debian:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-flask \
    libuuid1 \
    libstdc++6 \
    libgcc-s1 \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY run.sh /app/run.sh
COPY ptz_service.py /app/ptz_service.py
COPY sdk /app/sdk

RUN chmod a+x /app/run.sh

CMD ["/app/run.sh"]