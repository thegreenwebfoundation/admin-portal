# Troubleshooting

This page provides guidance about the various tooling we have for troubleshooting and debugging issues in the behaviour of our platform.

The first things you need to know about are listed below


- Our runbook
- Running a django instance connected to production and staging environments
- Sentry

## Our runbook - steps to follow when dealing with a live issue in production

We maintain a run book for troubleshooting live issues. It is listed in the private github repository used for maintaining our server infrastructure. If you're allowed to deploy to production, you should have access to this runbook, as well as the services it lists, like Loki/Grafna  for log aggregation, Sentry for exception tracking.

See [the runbook](https://github.com/thegreenwebfoundation/infra/blob/master/docs/runbook.md)

## Connecting a django instance to production / staging

It is possible to connect a local development instance, or a hosted one on gitpod, to either the staging environment, or in some special cases to the production environment for reproducing and fixing issues.

Use `dotenv`, passing in the path to the correct `dotenv` file, like `.env.prod` or `.env.staging` to run a command with different environment variables set - like connecting to a specific database, use a special DJANGO_SETTINGS config file, and so on.

For example, if you are running a local dev environment, and you have a `.env` file called .`env.staging.local`, running the code below would run the basic django command, connected to the servers outlined in .`env.staging.local`. This would use whatever django settings file is specified in that file, i.e. a file at `greenweb/settings/staging.py`.

```
dotenv -f .env.prod.local run -- ./manage.py
```


## Sentry

Sentry is set up to catch all uncaught exceptions in our software. In some cases, exceptions raised in dependencies are not caught, but handled in other error handling code that recovers from the error gracefully with a retry, but still shows up in our notification.

This means that if there is an error visible in Sentry, it doesn't automatically mean a human  has seen a page fail to load, or an API has returned a 500.

https://greenweb.sentry.io/issues/

Still, exceptions where possible should be caught, to that isn't unsuably noisy.

## Style and coding conventions.

Where possible, we aim to follow the guidance in the Octopus Energy Style guide for [python](https://github.com/octoenergy/public-conventions/blob/master/conventions/python.md), and [django](https://github.com/octoenergy/public-conventions/blob/main/conventions/django.md). We also prefer our functions to be type annotated where possible.

There's a lot of legacy code in the codebase, so our current rule of thumb is that in any given PR, if we touch a given file of code, we bring it up to standard, rather than attempting to do the whole app at once.

### See also:


https://www.loggly.com/blog/exceptional-logging-of-exceptions-in-python/
