FROM python:3.6-alpine
LABEL maintainer="jonathan@argpar.se"

ENV PYTHONUNBUFFERED 1

# init
RUN apk --no-cache add --update \
    bash \
    postgresql-client \
    postgresql-dev \
    build-base \
    gettext \
    && pip install pip --upgrade \
    && pip install pipenv

# app directory
RUN mkdir /app
WORKDIR /app

# Copy dependency first to reduce rebuild time
COPY Pipfile /app/
COPY Pipfile.lock /app/

ARG PIPENV_CFG

# setup
RUN pipenv install --system --deploy $PIPENV_CFG

COPY . /app

RUN ["chmod", "+x", "docker-entrypoint.sh"]

# CMD [ "python", "manage.py" ]
ENTRYPOINT [ "./docker-entrypoint.sh" ]
