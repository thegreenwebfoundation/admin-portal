FROM gitpod/workspace-mysql

# install Redis - we might not need ot remove the apt-lists bit
RUN sudo apt-get update  && sudo apt-get install -y   redis-server  && sudo rm -rf /var/lib/apt/lists/*

# install RabbitMQ
RUN sudo apt-get update  && sudo apt-get install rabbitmq-server -y --fix-missing && sudo rm -rf /var/lib/apt/lists/*