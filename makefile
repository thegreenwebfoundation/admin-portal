
## Installing
release:
	sentry-cli releases new -p admin-portal $(shell sentry-cli releases propose-version)
	sentry-cli releases set-commits --auto $(shell sentry-cli releases propose-version)
	ansible-playbook ansible/deploy.yml -i ansible/inventories/prod
	sentry-cli releases finalize $(shell sentry-cli releases propose-version)

.PHONY: release