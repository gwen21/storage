FROM alpine:latest

MAINTAINER Pôle EOLE <eole@ac-dijon.fr>


RUN apk add --no-cache --update curl openssl python3 py3-pip python3-dev git py3-aiohttp
RUN wget https://dl.minio.io/server/minio/release/linux-amd64/minio && \
    chmod +x minio && \
    mkdir /data

# Installation du pilote de services
ARG CONTAINERPILOT_VERSION=3.4.3
RUN export checksum=e8258ed166bcb3de3e06638936dcc2cae32c7c58 \
    && curl -Lso /tmp/containerpilot.tar.gz \
         "https://github.com/joyent/containerpilot/releases/download/${CONTAINERPILOT_VERSION}/containerpilot-${CONTAINERPILOT_VERSION}.tar.gz" \
    && echo "${checksum}  /tmp/containerpilot.tar.gz" | sha1sum -c \
    && tar zxf /tmp/containerpilot.tar.gz -C /usr/local/bin \
    && rm /tmp/containerpilot.tar.gz

RUN git clone https://github.com/minio/minio-py && \
    cd minio-py && \
    python3 setup.py install

ADD storage-minio/minio_config.json /root/.minio/config.json
EXPOSE 9000


CMD /minio server /data

