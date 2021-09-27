# Installation


This is a 3.2 Django project, running on MySQL, and using RabbitMQ as a message queue, and Redis for caching.

It is tested on OS X and linux systems.

To install it, create a virtual environment, and install the required packages.

```
make venv
. venv/bin/activate
pip install pipenv
pipenv install
```

### Set up the environment

By default, pipenv loads the contents of `.env` for any commands like opening a shell with `pipenv shell`, or running one off commands with `pipenv run command_name`.

Copy the sample environemnt file at `.env.sample` to `.env`, and fill in the necessary environment variables:

In production the admin_portal project relies on object storage for storing static files, but in development you may not need this.




