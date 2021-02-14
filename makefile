
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


.PHONY: release
