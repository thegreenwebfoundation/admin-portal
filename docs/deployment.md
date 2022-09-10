## Deployment
```{admonition} Draft
As a ... you probably want to deploy your work at some point. The following steps will guide you through the process of deploying your work.
```

### Github conventions
....

### Using Ansible
....

We use Ansible to deploy versions of the site to our servers.

More specifically, when we merge into the main/master branch, it triggers a deploy to production automatically, running the `deploy` playbook.

This runs through the following steps:

- check python and nodejs installed at recent versions
- fetch dependencies for both cases
- run build steps to generate static files for django and any artefacts needed in front end pipelines
- reload the servers
- if necessary, update nginx






