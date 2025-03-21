set dotenv-load := true

_default:
    just --list

# used for tagging our docker images.
TAG := `echo $$APP_RELEASE-$(git log -n 1 --format=%h)`

## Deploy a new release to production. This will not work in a Github Codespace, as it relies on staff SSH keys for deployment.
release:
    uv run sentry-cli releases new -p admin-portal `sentry-cli releases propose-version`
    uv run sentry-cli releases set-commits --auto `sentry-cli releases propose-version`
    uv run ansible-playbook ansible/deploy.yml -i ansible/inventories/prod.yml
    uv run sentry-cli releases finalize `sentry-cli releases propose-version`

# Create a super user for local development using the basic django `createsuperuser` command.
_dev_setup_local_users:
    uv run python ./manage.py createsuperuser --username admin --email admin@admin.com --noinput
    uv run python ./manage.py set_fake_passwords

# Run the django database migrations
_dev_setup_migrations:
    uv run python manage.py migrate

# Run a django development server that reloads when code is changed.
dev_runserver:
    uv run python manage.py runserver 0.0.0.0:$PORT

# Install the front end dependencies.
_dev_tailwind_install:
    uv run python manage.py tailwind install

# Run a django management command in the development environment.
dev_manage *options:
    uv run python manage.py {{ options }}

# Start the tailwind watcher - this will re-run tailwind to generate css as code is changed.
dev_tailwind_start: _dev_tailwind_install
    uv run python manage.py tailwind start

# Run the django tests on a loop with with pytest, and re-running them when code is changed.
dev_test *options:
    uv run pytest -s --create-db --looponfail --ds=greenweb.settings.testing {{ options }}

# Run the django tests on a loop with pytest, but only ones marked with `only`.
dev_test_only *options:
    uv run pytest -s --create-db --looponfail -m only -v --ds=greenweb.settings.testing {{ options }}

# Set up a development environment inside Github Codespaces
dev_setup_codespaces: _dev_setup_migrations _dev_tailwind_install _dev_setup_local_users
    uv run python manage.py tailwind build
    cd ./apps/theme/static_src/ && npx rollup --config
    uv run python manage.py collectstatic --no-input
    echo "all set up. run 'just dev_runserver' to start a server, and in another terminal "

# # Set up the github repo for data analysis against the Green Web Platform database. Will not work inside a Github Codespace
_data_analysis_repo:
    #!/usr/bin/env bash
    if test -d data-analysis; then
        echo "data-analysis repo already checked out"
    else
        git clone https://github.com/thegreenwebfoundation/data-analysis.git
    fi

# Start a Marimo notebook session from a starter notebook. This will not work inside a Github Codespace
data_marimo_starter *options: _data_analysis_repo
	# set up our start notebook with django initialised ready for queries
	uv run marimo edit data-analysis/starter-notebook.py {{ options }}

# Run Marimo notebook session. This will not work inside a Github Codespace
data_marimo *options: _data_analysis_repo
    uv run marimo {{ options }}

# Run the django tests (with pytest), creating a test database using the `testing` settings.
test *options:
    uv run pytest -s --create-db --ds=greenweb.settings.testing {{ options }}

# As above, but only the tests marked 'only'.
test_only *options:
    uv run pytest -s --create-db -m only -v --ds=greenweb.settings.testing {{ options }}

# Run a command with installed python tools available via 'uv', and environment variables via 'just'
run *options:
    uv run  {{ options }}

# Build the documentation using Sphinx.
docs:
    uv run sphinx-build ./docs _build/

# Build the documentation using Sphinx and keep updating it on every change.
docs_watch:
    uv run sphinx-autobuild ./docs _build/ --host 0.0.0.0

# Make a docker image for publishing to our registry.
docker_build:
    docker build -t $(APP_NAME)

# Push the current tagged image to our registry.
docker_release:
    docker tag $(APP_NAME) $(DOCKER_REGISTRY):$(TAG)
    docker push $(DOCKER_REGISTRY)/$(APP_NAME):$(TAG)

test_term:
    echo $TERM
