# Working with Docker


```{admonition} Under (re-)construction
:class: warning

Docker set up for this project isn't working at present - sorry about that. [See issue #635 for more](https://github.com/thegreenwebfoundation/admin-portal/pull/635)

```


We use Docker to create packaged versions of the platform for use where a dockerised version of this code base is expected.

The key scenarios we would use this would be

- in local development with docker compose
- where running code is assumed to be ephemeral, like a 'serverless' service (for example, AWS Lambda, Fly.io, Scaleway Serverless Containers, Google Cloud Run, etc.)
- in tooling used to understand the resource usage of the platform, like Green Coding Solution's Green Metrics Tool (GMT)


### How do use docker and docker compose for development

First, make sure you have docker or docker-compatible software installed (Orbstack on MacOS is a good example of the latter).

The Green Web Platform is comprised of three main services

- a WSGI django application: served by the Gunicorn webserver
- a message queue: RabbitMQ
- a database: MariaDB

This topology is represented in our Gitpod development environment, but also the Docker Compose file, `compose.yaml`, which is consumed by the Green Metrics Tool for testing runs.

#### Running a local version of the full system with docker compose

You can spin up a local version of the setup above with Docker Compose by checking you are in the project root directory, and calling:

```shell
# build the images locally, fetching the other images where needed
docker compose build
# run the services and main django application
docker compose up
```

This will download the various images needed, then start them as separate docker containers. By default the contents of the project `./apps` contianing most of the django code, and `./greenweb` directory are mounted into the running django container, allowing you to make changes. 

Similarly, an `.env.docker` file is used to provide the environment variables file that would be present in production, or in other development environments. See `.env.docker.sample` for an annotated list of the expected environment variables.

```yml
# abridged file - see compose.yaml for more details
django:
    env_file:
    - path: ./.env.docker
    build:
      context: .
      dockerfile: Dockerfile
    container_name: greenweb-app
    image: greenweb-app
    expose:
      - 9000
    ports:
      - 9000:9000
    volumes:
      - ./apps:/app/apps
      - ./greenweb:/app/greenweb
    restart: always
    depends_on:
      - db
      - rabbitmq
```

#### Running a local version of the django app docker

The green web platform is designed so that the different parts can be run on different servers, in various configurations.

To run just the django application, once the container is built, you can run it like so:

```
docker run  --env-file .env.prod.docker  -it greenweb-app bash
```

This will log you into the running container, where you can run `gunicorn` to serve web requests, and put greenchecks onto a message queue for looking up:

```
gunicorn --bind 0.0.0.0:9000 --config gunicorn.conf.py greenweb.wsgi
```


Or the `dramatiq` workers that take domains to off the message queue, look them up, and writ the results to lookup table:

```shell
# run dramatiq, with one thread and one process, listening on all queues
python ./manage.py rundramatiq --threads 1 --process 1
```

###  Making new images

If you are using docker you will at some point need to make new images.

Running long commands in the terminal gets tedious, so the `build_containers` script for annotated notes for a script to building a docker image.

There is a Makefile task intended for automating the process of creating builds - see `docker.build`



### Publish an image

Once you have an image built, to use it outside a development environment it needs to be accessible over the internet. At a high level the steps are:

1. build the image
1. tag the image
1. push the image to a registry

There is a Makefile task set up for this - see `docker.release` - this tags and pushes a built image to a docker repository hosted by Scaleway. You will need to be authenticated first. 

```shell 
docker login <SCALEWAY_DOCKER_REGISTRY>/<GREENWEB_NAMESPACE> -u nologin
```

You will be prompted for a password - if you don't have access to these credentials, please contact one of the green web staff.
