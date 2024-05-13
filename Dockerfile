FROM python:3.11 as production


RUN apt-get update
RUN apt-get upgrade --yes
RUN apt-get install wget --no-install-recommends --yes
RUN wget https://deb.nodesource.com/setup_18.x -O /tmp/setup_18.x.sh --no-check-certificate
RUN bash /tmp/setup_18.x.sh
RUN apt-get install nodejs --no-install-recommends --yes


# Install dependencies in a virtualenv
ENV VIRTUAL_ENV=/app/.venv

RUN useradd deploy --create-home && mkdir /app $VIRTUAL_ENV && chown -R deploy /app $VIRTUAL_ENV

WORKDIR /app

# Set default environment variables. They are used at build time and runtime.
# If you specify your own environment variables on Heroku, they will
# override the ones set here. The ones below serve as sane defaults only.
#  * PATH - Make sure that Poetry is on the PATH, along with our venv
#  * PYTHONPATH - Ensure `django-admin` works correctly.
#  * PYTHONUNBUFFERED - This is useful so Python does not hold any messages
#    from being output.
#    https://docs.python.org/3.9/using/cmdline.html#envvar-PYTHONUNBUFFERED
#    https://docs.python.org/3.9/using/cmdline.html#cmdoption-u
#  * DJANGO_SETTINGS_MODULE - default settings used in the container.
#  * PORT - default port used. Please match with EXPOSE.
ENV PATH=$VIRTUAL_ENV/bin:$PATH \
    PYTHONPATH=/app
#     PYTHONUNBUFFERED=1 \
#     DJANGO_SETTINGS_MODULE=greenweb.settings.production \
#     PORT=9000 \
#     WEB_CONCURRENCY=3 \
#     GUNICORN_CMD_ARGS="-c gunicorn-conf.py --max-requests 1200 --max-requests-jitter 50 --access-logfile - --timeout 25 --reload"

# Port exposed by this container. Should default to the port used by your WSGI
# server (Gunicorn). Heroku will ignore this.
EXPOSE 9000

USER deploy

# Install your app's Python requirements.
RUN python -m venv $VIRTUAL_ENV
RUN python -m pip install uv wheel --upgrade


# Copy application code.
COPY --chown=deploy . .


# install dependencies via UV
RUN uv pip install -r requirements/requirements.linux.generated.txt 

# set up front end pipeline
RUN python ./manage.py tailwind install
RUN python ./manage.py tailwind build

# # # run npx rollup in correct directory
RUN cd ./apps/theme/static_src/ && \
    npx rollup --config

# # TODO Collect static. This command will move static files from application
# # directories and "static_compiled" folder to the main static directory that
# # will be served by the WSGI server.
RUN python ./manage.py collectstatic --noinput --clear
