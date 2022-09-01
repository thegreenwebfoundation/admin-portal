# Installation

This installation shows you how to setup the Admin Portal of The Green Web Foundation.

In order to setup this project, we recommend following the guides from top to bottom. Skipping some topics might result in missing crucial steps for the project to work.

---
## Development on a remote machine using Gitpod
### Why Gitpod
This is the main supported approach for setting up a development environment. You can use other approaches, but we may not be able to provide as much support. Gitpod will spin and configure a development environment for you, to which you can connect either from your IDE or from the browser. By choosing this approach you don't have to manually install any dependencies.
 
### Preparing a Gitpod workspace
After logging into Gitpod or creating an account we recommend also installing the Gitpod browser extension. This extension integrates extra functionality in websites such as Github.

1. Go to our [Github repository](https://github.com/thegreenwebfoundation/admin-portal) and click on the Gitpod button if you have the browser extention installed or manually create and link it in your Gitpod Workspaces. It might take a couple of minutes to prepare the environment.
2. After Gitpod is finished preparing the environment, it will open the workspace. Close any unnecessary terminal windows. To open a new fresh terminal window press ```Ctrl + ` ```.
---
## Development on a local machine using virtual environments
In an isolated [virtual environment](https://docs.python.org/3/tutorial/venv.html) we are able to easily manage Python dependencies within the project. 

### Prerequisites
If you decide to go with this approach, you need to make sure you have the system dependencies installed. Use this command (if your OS uses `apt`) or equivalent for your operating system:
```
sudo apt install python3 python3-dev build-essential libmariadb3 libmariadb-dev
```

__Note__ In the context of development, it is recommended to manage Python versions using [`pyenv`](https://github.com/pyenv/pyenv) instead of relying on the version shipped in the operating system.

__Note__ Currently Python version 3.8.5 is used on production.

### Setup
Before following the following list, make sure you are in the root directory (workspace/admin-portal).
1. Start by creating a virtual environment named *venv* by executing the following command in a terminal window: `make venv`.
2. Now that the environment has been created, we can access it with the following command `. venv/bin/activate`.
3. Download a package named *pipenv* with *pip*: `pip install pipenv`.
4. Once downloaded, use this command to install all other packages: `pipenv install`.
5. As a final step, make sure to copy the content of `.env.test` to `.env` and add the necessary credentials.<br>

__Note__ that this project relies on object storage. In production this is needed to store static files, but in development it is not required.

By default `pipenv` loads the content of the `.env` file.<br>
For starting the project the shell command can be used like this `pipenv shell`.

## Working with email

This project has features that send email notifications to users. To test email functionality, this project uses [Mailhog](https://github.com/mailhog/MailHog). It's enabled by default in Gitpod environments, and you can access it on port 8025.
