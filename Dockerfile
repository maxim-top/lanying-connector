FROM docker.io/python:3.10

WORKDIR /app

COPY requirements.txt ./

RUN apt update && apt-get install -y gobject-introspection
RUN pip install --no-cache-dir -r requirements.txt
ENV GUNICORN_CMD_ARGS="--bind=0.0.0.0"
COPY *.py .
COPY services services
COPY configs configs
COPY templates templates
EXPOSE 8000

CMD [ "gunicorn", "--workers=5", "--threads=10", "--worker-class=gthread", "lanying_connector:app"]
