# set dotenv-load := true

default:
    just --list

# used for tagging our docker images.
TAG := `echo $$APP_RELEASE-$(git log -n 1 --format=%h)`

## Deploy a new release to production. This will not work in Gitpod, as it relies on staff SSH keys for deployment. 
release:
    uv run dotenv -f env.prod run -- sentry-cli releases new -p admin-portal `sentry-cli releases propose-version`
    uv run dotenv -f env.prod run -- sentry-cli releases set-commits --auto `sentry-cli releases propose-version`
    uv run dotenv -f env.prod run -- ansible-playbook ansible/deploy.yml -i ansible/inventories/prod.yml
    uv run dotenv -f env.prod run -- sentry-cli releases finalize `sentry-cli releases propose-version`

# Create a super user for local development using the basic django `createsuperuser` command.
dev_createsuperuser:
    uv run dotenv run -- python ./manage.py createsuperuser --username admin --email admin@admin.com --noinput
    uv run dotenv run -- python ./manage.py set_fake_passwords

# Run a django development server that reloads when codes is changed.
dev_runserver:
    uv run dotenv run -- python manage.py runserver

# Run a django management command in the development environment.
dev_manage *options:
    uv run dotenv run -- python manage.py {{ options }}

# Start the tailwind watcher - this will re-run tailwind to generate css as code is changed.
dev_tailwind_start:
    uv run dotenv run -- python manage.py tailwind start

# Install the front end dependencies.
dev_tailwind_install:
    uv run dotenv run -- python manage.py tailwind install

# Run the django tests on a loop with with pytest, and re-running them when code is changed.
dev_test:
    uv run uv dotenv run -- pytest -s --create-db --looponfail --ds=greenweb.settings.testing

# Run the django tests on a loop with pytest, but only ones marked with `only`.
dev_test_only:
    uv run dotenv run -- pytest -s --create-db --looponfail -m only -v --ds=greenweb.settings.testing

# # Set up the github repo for data analysis against the Green Web Platform database.
data_analysis_repo:
    #!/usr/bin/env bash
    if test -d data-analysis; then
        echo "data-analysis repo already checked out"
    else
        git clone https://github.com/thegreenwebfoundation/data-analysis.git
    fi

# Start a Marimo notebook session from a starter notebook
data_marimo_starter *options: data_analysis_repo
	# set up our start notebook with django initialised ready for queries
	uv run dotenv run -- marimo edit data-analysis/starter-notebook.py {{ options }}

# Run Marimo notebook session
data_marimo *options: data_analysis_repo
    uv run dotenv run -- marimo {{ options }}

# Run the django tests (with pytest), creating a test database using the `testing` settings.
test *options:
    uv run dotenv run -- pytest -s --create-db --ds=greenweb.settings.testing {{ options }}

# As above, but only the tests marked 'only'.
test_only:
    uv run dotenv run -- pytest -s --create-db -m only -v --ds=greenweb.settings.testing

# Build the documentation using Sphinx.
docs:
    uv run dotenv run -- sphinx-build ./docs _build/

# Build the documentation using Sphinx and keep updating it on every change.
docs_watch:
    uv run dotenv run -- sphinx-autobuild ./docs _build/

# Make a docker image for publishing to our registry.
docker_build:
    docker build -t $(APP_NAME)

# Push the current tagged image to our registry.
docker_release:
    docker tag $(APP_NAME) $(DOCKER_REGISTRY):$(TAG)
    docker push $(DOCKER_REGISTRY)/$(APP_NAME):$(TAG)
