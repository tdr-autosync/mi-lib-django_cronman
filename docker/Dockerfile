FROM 050946403637.dkr.ecr.ca-central-1.amazonaws.com/mi-infra-bullseye_slim:v1.0.0-py3.6-psql15 AS venv

COPY . /application/cronman
RUN . $HOME/.bashrc  && \
    pip install -Ur /application/cronman/requirements.txt  && \
    pip install --no-deps -e /application/cronman

WORKDIR /application/cronman
ENTRYPOINT ["/application/cronman/docker/entrypoint.sh"]
