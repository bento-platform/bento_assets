FROM python:3.14-alpine

ARG INSTANCE

COPY LICENSE manifest.json /assets/
COPY scripts/install.py /assets/install.py
COPY instances/${INSTANCE}/lib/ /assets/lib/

ENTRYPOINT ["python", "/assets/install.py"]
