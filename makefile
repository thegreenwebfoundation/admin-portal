.PHONY: release venv

# used for tagging our docker images.
TAG ?= $(shell echo $$APP_RELEASE)-$(shell git log -n 1 --format=%h)

# Create Python virtual environment if not yet created.
venv:
	test -d .venv || python -m venv .venv

## Deploy a new release to production. This will not work in Gitpod, as it relies on staff SSH keys for deployment. 
release:
	dotenv -f env.prod run -- sentry-cli releases new -p admin-portal $(shell sentry-cli releases propose-version)
	dotenv -f env.prod run -- sentry-cli releases set-commits --auto $(shell sentry-cli releases propose-version)
	dotenv -f env.prod run -- ansible-playbook ansible/deploy.yml -i ansible/inventories/prod.yml
	dotenv -f env.prod run -- sentry-cli releases finalize $(shell sentry-cli releases propose-version)

# Create a super user for local development using the basic django `createsuperuser` command.
dev.createsuperuser:
	dotenv run -- python ./manage.py createsuperuser --username admin --email admin@admin.commits --noinput
	dotenv run -- python ./manage.py set_fake_passwords

# Run a django development server that reloads when codes is changed.
dev.runserver:
	dotenv run -- python manage.py runserver

# Start the tailwind watcher - this will re-run tailwind to generate css as code is changed.
dev.tailwind.start:
	dotenv run -- python manage.py tailwind start

# Install the front end dependencies.
dev.tailwind.install: 
	dotenv run -- python manage.py tailwind install

# Run the django tests on a loop with with pytest, and re-running them when code is changed.
dev.test:
	dotenv run -- pytest -s --create-db --looponfail --ds=greenweb.settings.testing

# Run the django tests on a loop with pytest, but only ones marked with `only'.
dev.test.only:
	dotenv run -- pytest -s --create-db --looponfail -m only -v  --ds=greenweb.settings.testing

# Set up the github repo for data analysis against the Green Web Platform database.
data_analysis_repo:
	if test -d data-analysis; \
	then echo "data-analysis repo already checked out";  \
	else git clone https://github.com/thegreenwebfoundation/data-analysis.git; \
	fi

# Start a Marimo notebook session.
notebook.gitpod: data_analysis_repo
	# set up our start notebook with django initialised ready for queries
	dotenv run -- marimo edit data-analysis/starter-notebook.py


# Run the django tests (with pytest), creating a test database using the `testing` settings.
test:
	dotenv run -- pytest -s --create-db --ds=greenweb.settings.testing

# As above, but only the tests marked 'only'.
test.only:
	dotenv run -- pytest -s --create-db -m only -v  --ds=greenweb.settings.testing

# Build the documentation using Sphinx.
docs:
	dotenv run -- sphinx-build ./docs _build/

# Build the documentation using Sphinx and keep updating it on every change.
docs.watch:
	dotenv run -- sphinx-autobuild ./docs _build/

# Make a docker image for publishing to our registry.
docker.build:
	docker build -t $(APP_NAME)

# Push the current tagged image to our registry.
docker.release:	
	docker tag $(APP_NAME) $(DOCKER_REGISTRY):$(TAG)
	docker push $(DOCKER_REGISTRY)/$(APP_NAME):$(TAG)
