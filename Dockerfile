FROM ubuntu:16.04

RUN apt-get update && apt-get install -y build-essential python-dev openssl libssl-dev libevent-dev git python-pip 

# create the user to run volttron
RUN useradd -ms /bin/bash volttron_user
RUN mkdir /home/volttron_user/volttron
RUN chown -R volttron_user:volttron_user /home/volttron_user/volttron

#change user to volttron_user
USER volttron_user
WORKDIR /home/volttron_user

RUN git clone https://github.com/VOLTTRON/volttron.git

# run bootstrap.py as the volttron_user
WORKDIR /home/volttron_user/volttron

RUN python bootstrap.py

ENV BASH_ENV /home/volttron_user/volttron/env/bin/activate
RUN . env/bin/activate
RUN volttron -vv -l volttron.log&

