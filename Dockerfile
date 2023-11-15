FROM almalinux:9-minimal

LABEL org.opencontainers.image.source=https://github.com//PavloKuptsov/geo-proxy \
      org.opencontainers.image.description='Geo-proxy for DOA'

RUN --mount=type=cache,sharing=private,target=/var/cache/yum <<EOR
    set -ex
    microdnf update -y --refresh
    microdnf --setopt=install_weak_deps=0 --best --nodocs -y install shadow-utils python3.11-pip python3.11-wheel \
        usbutils gcc python3.11-devel
    mkdir -p /root/geo-proxy

EOR

ENV PATH="/root/geo-proxy/.local/bin:${PATH}"
COPY requirements.txt *.py /root/geo-proxy/
COPY src /root/geo-proxy/src/
WORKDIR /root/geo-proxy/
RUN pip3.11 install -r requirements.txt

ENTRYPOINT ["python3.11", "/root/geo-proxy/server.py"]
