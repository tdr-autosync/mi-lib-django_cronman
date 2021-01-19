FROM uhinfra/centos7-python:v19-3.6-psql10

COPY . /application/cronman
RUN source $HOME/.bashrc  && \
    pip install -Ur /application/cronman/requirements.txt  && \
    pip install --no-deps -e /application/cronman

WORKDIR /application/cronman
ENTRYPOINT ["/application/cronman/docker/entrypoint.sh"]
