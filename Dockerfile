FROM python:3.9-alpine

RUN apk add -U git tini

COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt
COPY deconflicter.py /app/

WORKDIR /logseq
ENTRYPOINT [ "/sbin/tini", "--" ]
CMD [ "python", "/app/deconflicter.py" ]
