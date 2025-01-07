# Installation

This installation shows you how to setup the Admin Portal of the Green Web Foundation.

In order to setup this project, we recommend following the guides from top to bottom. Skipping some topics might result in missing crucial steps for the project to work.

---

## Development on a remote machine using Gitpod

### Why Gitpod

This is the main supported approach for setting up a development environment. You can use other approaches, but we may not be able to provide as much support. Gitpod will spin and configure a development environment for you, to which you can connect either from your IDE or from the browser. By choosing this approach you don't have to manually install any dependencies.

### Preparing a Gitpod workspace

After logging into Gitpod or creating an account we recommend also installing the Gitpod browser extension. This extension integrates extra functionality in websites such as Github.

1. Go to our [Github repository](https://github.com/thegreenwebfoundation/admin-portal) and click on the Gitpod button if you have the browser extention installed or manually create and link it in your Gitpod Workspaces. It might take a couple of minutes to prepare the environment.

2. After Gitpod is finished preparing the environment, it will open the workspace. Close any unnecessary terminal windows. To open a new fresh terminal window press ```Ctrl + ` ```.

3. In almost all cases, you will need to have a _virtual environment_ set up so that the necessary commands for Django and other libraries are available to you. You can enter a virtual environment by typing `source .venv/bin/activate` from the the project root (i.e. `/workspace/admin-portal/`). You can tell you're a virtual environment - because your prompt will change from `gitpod /workspace/admin-portal (BRANCH_NAME) $` to `(.venv) gitpod /workspace/admin-portal (BRANCH_NAME) $`. Want more? [Learn more about virtual environments for python](https://realpython.com/python-virtual-environments-a-primer/).

4. There is a makefile set up, to allow easy access to common tasks like running a development server, spinning up tailwind for front end development, creating a superuser and so on. There is tab-completion set up in Gitpod - so to see the options available, type `make` and hit tab in a new terminal. You should see output like below:

```
(.venv) gitpod /workspace/admin-portal (BRANCH_NAME) $ make 
data_analysis_repo    dev.tailwind.start    docker.release        release               
dev.createsuperuser   dev.test              docs                  test                  
dev.runserver         dev.test.only         docs.watch            test.only             
dev.tailwind.install  docker.build          notebook.gitpod       venv                  
```

Open the makefile to read the docs about what each command does.

---

## Development on a local machine using virtual environments

In an isolated [virtual environment](https://docs.python.org/3/tutorial/venv.html) we are able to easily manage Python dependencies within the project.

### Prerequisites

If you decide to go with this approach, you need to make sure you have the system dependencies installed. Use this command (if your OS uses `apt`) or equivalent for your operating system:

```
sudo apt install python3 python3-dev build-essential libmariadb3 libmariadb-dev
```

__Note__ In the context of development, it is recommended to manage Python versions using [`pyenv`](https://github.com/pyenv/pyenv) instead of relying on the version shipped in the operating system.

__Note__ Currently Python version 3.11.9 is used in production.

### Setup

Before following the following list, make sure you are in the root directory (workspace/admin-portal).

1. Make sure you have the right Python version installed: `python --version`
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment created for you: `source .venv/bin/activate`
4. Install a package named `uv` with `pip`: `python -m pip install uv`.
5. Once installed, use this command to install all project packages: `uv pip install -r`. The project packages are defined in `requirements.dev.generated.txt`.
5. As a final step, make sure to copy the content of `.env.test` to `.env` and add the necessary credentials.

__Note__ that this project relies on object storage. In production this is needed to store static files, but in development it is not required.

By default `dotenv run` loads the content of the `.env` files before the next command, so

```
dotenv run -- my-command
```

Will run my-command with all the environment variables in .env set.

## Working with email

This project has features that send email notifications to users. To test email functionality, this project uses [Mailhog](https://github.com/mailhog/MailHog). It's enabled by default in Gitpod environments, and you can access it on port 8025.

## Working with Docker

If you prefer working with docker, there are instructions for spinning up a local environment with `docker compose` and building docker images. See [working with docker](working-with-docker.md) for more.
