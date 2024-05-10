FROM gitpod/workspace-python

# install Redis - we might not need ot remove the apt-lists bit


RUN sudo apt-get update  && sudo apt-get install -y build-essential libmariadb-dev libmariadbclient-dev libmariadb3 mariadb-client mariadb-common && sudo rm -rf /var/lib/apt/lists/*

# install RabbitMQ
RUN sudo apt-get update  && sudo apt-get install rabbitmq-server -y --fix-missing && sudo rm -rf /var/lib/apt/lists/*

# https://www.gitpod.io/docs/introduction/languages/python
RUN pyenv install 3.11 \
    && pyenv global 3.11

RUN python -m pip install --upgrade pip uv