set dotenv-load := true

default:
    just --list

# used for tagging our docker images.
TAG := `echo $$APP_RELEASE-$(git log -n 1 --format=%h)`

## Deploy a new release to production. This will not work in Gitpod, as it relies on staff SSH keys for deployment. 
release:
    uv run sentry-cli releases new -p admin-portal `sentry-cli releases propose-version`
    uv run sentry-cli releases set-commits --auto `sentry-cli releases propose-version`
    uv run ansible-playbook ansible/deploy.yml -i ansible/inventories/prod.yml
    uv run sentry-cli releases finalize `sentry-cli releases propose-version`

# Create a super user for local development using the basic django `createsuperuser` command.
dev_createsuperuser:
    uv run python ./manage.py createsuperuser --username admin --email admin@admin.com --noinput
    uv run python ./manage.py set_fake_passwords

# Run a django development server that reloads when codes is changed.
dev_runserver:
    uv run python manage.py runserver 0.0.0.0:$PORT

# Run a django management command in the development environment.
dev_manage *options:
    uv run python manage.py {{ options }}

# Start the tailwind watcher - this will re-run tailwind to generate css as code is changed.
dev_tailwind_start:
    uv run python manage.py tailwind start

# Install the front end dependencies.
dev_tailwind_install:
    uv run python manage.py tailwind install

# Run the django tests on a loop with with pytest, and re-running them when code is changed.
dev_test:
    uv run pytest -s --create-db --looponfail --ds=greenweb.settings.testing

# Run the django tests on a loop with pytest, but only ones marked with `only`.
dev_test_only:
    uv run pytest -s --create-db --looponfail -m only -v --ds=greenweb.settings.testing

dev_setup_migrations:
    uv run python manage.py migrate

# set up 
dev_setup_codespaces: dev_setup_migrations dev_tailwind_install dev_createsuperuser 
    uv run python manage.py tailwind build
    cd ./apps/theme/static_src/ && npx rollup --config
    uv run python manage.py collectstatic --no-input    
    echo "all set up. run 'just dev_runserver' to start a server, and in another terminal "

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
	uv run marimo edit data-analysis/starter-notebook.py {{ options }}

# Run Marimo notebook session
data_marimo *options: data_analysis_repo
    uv run marimo {{ options }}

# Run the django tests (with pytest), creating a test database using the `testing` settings.
test *options:
    uv run pytest -s --create-db --ds=greenweb.settings.testing {{ options }}

# As above, but only the tests marked 'only'.
test_only:
    uv run pytest -s --create-db -m only -v --ds=greenweb.settings.testing

# Run a command with 'uv' set up and just setting up the environment variables
run *options:
    uv run  {{ options }}

# Build the documentation using Sphinx.
docs:
    uv run sphinx-build ./docs _build/

# Build the documentation using Sphinx and keep updating it on every change.
docs_watch:
    uv run sphinx-autobuild ./docs _build/

# Make a docker image for publishing to our registry.
docker_build:
    docker build -t $(APP_NAME)

# Push the current tagged image to our registry.
docker_release:
    docker tag $(APP_NAME) $(DOCKER_REGISTRY):$(TAG)
    docker push $(DOCKER_REGISTRY)/$(APP_NAME):$(TAG)
