FROM python:3.8.5-slim-buster
MAINTAINER Kirill Malyshev "kirill.malyshe@gmail.com"

RUN apt-get update \
&& apt-get install gcc gettext -y \
&& apt-get clean

# installing security updates
RUN apt-get update && apt install -y unattended-upgrades && unattended-upgrade -d && apt purge -y unattended-upgrades

ENV PYTHONUNBUFFERED 1
ENV HOME_DIR=/django_example
WORKDIR $HOME_DIR
RUN rm -rf $HOME_DIR && mkdir $HOME_DIR

RUN mkdir -p $HOME_DIR/client_config && \
mkdir -p $HOME_DIR/static && \
mkdir -p $HOME_DIR/media && \
mkdir -p $HOME_DIR/django_example/static && \
mkdir -p $HOME_DIR/django_example/components \
mkdir -p $HOME_DIR/django_example/media

RUN pip install pip -U
COPY ./req_dev.txt req_dev.txt
RUN pip install -r req_dev.txt

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . $HOME_DIR
