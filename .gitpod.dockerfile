FROM gitpod/workspace-mysql

# install Redis
RUN sudo apt-get update  && sudo apt-get install -y   redis-server  && sudo rm -rf /var/lib/apt/lists/*

# install RabbitMQ
RUN sudo apt-get install rabbitmq-server -y --fix-missing