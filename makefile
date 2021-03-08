.PHONY: release venv

# Create Python virtual environment if not yet created.
venv:
	test -d venv || python3 -m venv venv

## Installing
release:
	PIPENV_DOTENV_LOCATION=.env.prod pipenv run sentry-cli releases new -p admin-portal $(shell sentry-cli releases propose-version)
	PIPENV_DOTENV_LOCATION=.env.prod pipenv run sentry-cli releases set-commits --auto $(shell sentry-cli releases propose-version)
	PIPENV_DOTENV_LOCATION=.env.prod pipenv run ansible-playbook ansible/deploy.yml -i ansible/inventories/prod
	PIPENV_DOTENV_LOCATION=.env.prod pipenv run sentry-cli releases finalize $(shell sentry-cli releases propose-version)

dev.test:
	pytest -s --create-db --looponfail

dev.test.only:
	pytest -s --create-db --looponfail -m only -v

test.only:
	pytest -s --create-db -m only -v

flake:
	flake8 ./greenweb ./apps ./*.py --count --statistics

black:
	black ./greenweb ./apps ./*.py $(ARGS)

black.check:
	@ARGS="--check --color --diff" make black

ci: | black.check flake
