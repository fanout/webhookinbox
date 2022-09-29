FROM python:3.10

RUN apt update
RUN apt install -y supervisor apt-transport-https software-properties-common gnupg python3-pip
RUN echo deb https://fanout.jfrog.io/artifactory/debian fanout-focal main | tee /etc/apt/sources.list.d/fanout.list
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EA01C1E777F95324
RUN apt update

RUN apt install -y pushpin

RUN apt clean && apt autoclean && rm -fr /var/lib/apt/lists/* && rm -fr /tmp/*

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
COPY ./ /app

WORKDIR /
COPY pushpin.conf /etc/pushpin
COPY internal.conf /usr/lib/pushpin
COPY routes /etc/pushpin

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord"]
