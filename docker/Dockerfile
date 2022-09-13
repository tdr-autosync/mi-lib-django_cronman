FROM uhinfra/bullseye:v2.0.3-py3.6-psql10-node12

COPY . /application/cronman
RUN . $HOME/.bashrc  && \
    pip install -Ur /application/cronman/requirements.txt  && \
    pip install --no-deps -e /application/cronman

WORKDIR /application/cronman
ENTRYPOINT ["/application/cronman/docker/entrypoint.sh"]
