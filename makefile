.PHONY: release venv

# Create Python virtual environment if not yet created.
venv:
	test -d venv || python3 -m venv venv

## Installing
release:
	dotenv -f env.prod run -- sentry-cli releases new -p admin-portal $(shell sentry-cli releases propose-version)
	dotenv -f env.prod run -- sentry-cli releases set-commits --auto $(shell sentry-cli releases propose-version)
	dotenv -f env.prod run -- ansible-playbook ansible/deploy.yml -i ansible/inventories/prod.yml
	dotenv -f env.prod run -- sentry-cli releases finalize $(shell sentry-cli releases propose-version)

dev.createsuperuser:
	python ./manage.py createsuperuser --username admin --email admin@admin.commits --noinput
	python ./manage.py set_fake_passwords

dev.runserver:
	python manage.py runserver

# start the tailwind watcher
dev.tailwind.start:
	python manage.py tailwind start

# install the front end dependencies
dev.tailwind.install:
	python manage.py tailwind install

dev.test:
	pytest -s --create-db --looponfail --ds=greenweb.settings.testing

dev.test.only:
	pytest -s --create-db --looponfail -m only -v  --ds=greenweb.settings.testing

data_analysis_repo:
	if test -d data-analysis; \
	then echo "data-analysis repo already checked out";  \
	else git clone https://github.com/thegreenwebfoundation/data-analysis.git; \
	fi

# start a marimo notebook session
notebook.gitpod: data_analysis_repo
	# set up our start notebook with django initialised ready for queries
	marimo edit data-analysis/starter-notebook.py



# Run a basic test(with pytest) that creates a database using the testing settings
test:
	pytest -s --create-db --ds=greenweb.settings.testing

test.only:
	pytest -s --create-db -m only -v  --ds=greenweb.settings.testing

# Build the documentation using Sphinx
docs:
	sphinx-build ./docs _build/

# Build the documentation using Sphinx and keep updating it on every change
docs.watch:
	sphinx-autobuild ./docs _build/
