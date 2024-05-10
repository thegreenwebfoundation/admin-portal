FROM gitpod/workspace-python

# install Mariadb
RUN sudo apt-get update \
    && sudo apt-get install -y \
    build-essential \
    libmariadb-dev libmariadb-dev-compat \
    mariadb-client mariadb-common \
    && sudo rm -rf /var/lib/apt/lists/*

# install RabbitMQ
RUN sudo apt-get update \
    && sudo apt-get install rabbitmq-server -y --fix-missing \
    && sudo rm -rf /var/lib/apt/lists/*

# https://www.gitpod.io/docs/introduction/languages/python
# Install the correct version of python
RUN pyenv install 3.11 \
    && pyenv global 3.11

# install a recent version of Node.js for front end work
RUN wget https://deb.nodesource.com/setup_18.x -O /tmp/setup_18.x.sh
RUN sudo bash /tmp/setup_18.x.sh
RUN sudo apt-get install -y nodejs
