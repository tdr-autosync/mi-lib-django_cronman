FROM uhinfra/centos7-python3.7:v13
MAINTAINER Motoinsight Infra-Team <infra@motoinsight.com>

ADD . /application/cronman
RUN pip install -e /application/cronman
# NOTE: django>=2.2 requires sqlite 3.8.3 and centos7 have only 3.7.X
RUN pip install pytest pytest-django sentry_sdk raven redis mock sql "django<2.2"
