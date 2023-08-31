FROM almalinux:9-minimal

LABEL org.opencontainers.image.source=https://github.com//PavloKuptsov/geo-proxy \
      org.opencontainers.image.description='Geo-proxy for DOA'

RUN microdnf update -y --refresh && \
    microdnf --setopt=install_weak_deps=0 --best --nodocs -y install shadow-utils python3.11-pip python3.11-wheel && \
    mkdir -p /root/geo-proxy && \
    microdnf clean all

ENV PATH="/root/geo-proxy/.local/bin:${PATH}"
COPY requirements.txt *.py /root/geo-proxy/
WORKDIR /root/geo-proxy/
RUN pip3.11 install -r requirements.txt

ENTRYPOINT ["python3.11", "/root/geo-proxy/server.py"]
