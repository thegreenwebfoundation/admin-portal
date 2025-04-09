FROM python:3.11 AS production

# Update the package listing, so we know what packages exist
RUN apt-get update

# Install security updates:
RUN apt-get upgrade --yes

# Install nodejs, so we are able to generate our front end bundles with tailwind
RUN curl https://deb.nodesource.com/setup_18.x > /tmp/setup_18.x.sh
RUN bash /tmp/setup_18.x.sh
RUN apt-get install nodejs --no-install-recommends --yes

# Delete cached files we don't need anymore
RUN apt-get clean

# Delete index files we don't need anymore:
RUN rm -rf /var/lib/apt/lists/*

# Install dependencies in a virtualenv
ENV VIRTUAL_ENV=/app/.venv
RUN useradd deploy --create-home && mkdir /app $VIRTUAL_ENV && chown -R deploy /app $VIRTUAL_ENV

WORKDIR /app

# Adding the virtual environment to the path saves us needing to 
# run `source /app/.venv/bin/activate`, and adding python path
# makes it easier to run manage.py commands
ENV PATH=$VIRTUAL_ENV/bin:$PATH \
    PYTHONPATH=/app

# Default port exposed by this container
EXPOSE 9000

# We don't want to use root. We use this user elsewhere without docker
# so we keep the same name for consistency
USER deploy

# Set up our virtual env directory
RUN python -m venv $VIRTUAL_ENV

# Add our python libraries for managing dependencies
RUN python -m pip install uv wheel --upgrade

# Copy just the pyproject.toml for uv sync.
# That way, the next step can be cached until pyproject.toml changes.
COPY --chown=deploy ./pyproject.toml ./pyproject.toml

# Install dependencies via uv
RUN uv sync

# Copy application code, with dockerignore filtering out the stuff we don't want
# from our final build artefact
COPY --chown=deploy . .

# Copy envfile to the correct location.
COPY --chown=deploy .env.docker .env

# Set up front end pipeline
RUN dotenv run -- python ./manage.py tailwind install
RUN dotenv run -- python ./manage.py tailwind build

# Install the other node dependencies
# TODO: we might not need node in production *at all* if we can generate 
# the static files in the build step. Investigate if this results 
# in meaningful savings on the final image size
WORKDIR /app
RUN cd ./apps/theme/static_src/ && \
    npx rollup --config

# Collect static files
RUN dotenv run -- python ./manage.py collectstatic --noinput --clear

# Use the shell form of CMD, so we have access to our environment variables
# $GUNICORN_CMD_ARGS allows us to add additional arguments to the gunicorn command
CMD gunicorn greenweb.wsgi --bind $GUNICORN_BIND_IP:$PORT --config gunicorn.conf.py $GUNICORN_CMD_ARGS
