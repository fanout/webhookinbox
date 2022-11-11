FROM  ubuntu:focal
ENV DEBIAN_FRONTEND noninteractive

RUN apt update
RUN apt install -y supervisor python3-pip cron

RUN apt clean && apt autoclean && rm -fr /var/lib/apt/lists/* && rm -fr /tmp/*

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY ./ /app

WORKDIR /

RUN (crontab -l ; echo "*/2 * * * * python3 /app/manage.py cleanup") | crontab
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord"]
