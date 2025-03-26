# Installation

This installation shows you how to setup the Admin Portal of the Green Web Foundation.

---

## Development on a remote machine using Github Codespaces

### Why Github Codespaces

This project uses Github Codespaces to provide managed, hosted development environments on Github, using the [devcontainer.json](https://containers.dev/) standard. This means you don't need to install project dependencies on your local computer if you don't want to. 

You can work in a browser or use a local editor like VS Code, or Vim to connect to the managed environment.


### Setting up a Github Codespace

1. Go to our [Github repository](https://github.com/thegreenwebfoundation/admin-portal) and click on the **Code** button and then the **Codespaces** tab.

![Github Codespaces button](img/screenshot-codespaces-button.png)


2. Next, either choose the **+** icon, to create a workspace on the default master branch with the default machine type to run code in, or the "three dots" icon to bring up the option of **New with Options**. 

![Github Codespaces create or new with options](img/screenshot-codespaces-option-for-setup.png)


3. If you choose new with options you can connect to a specific branch, and with a specific machine type, and region. Setting a region will allow you to run the codespace geographically closer to you, which can make it more responsive. Using a specific machine type can increase the resources available to you for running tests or general computation.

![Github Codespaces - options for 'new with options'](img/screenshot-codespaces-option-new-with-options.png)

4. Selecting your machine will either set up a new browser tab with your environment booting up or VS code locally to work in. The first step of creating an codespace can take a few minutes - be ready to get a hot drink.

5. Once an environment is set up, you should have a terminal available. Type `just` in the terminal to see your options. 

![Github Codespaces 'just' options ](img/screenshot-codespaces-just-options.png)

6. If you want to see a running local instance of the platform, choose `dev_runserver`. You should be able to access see a local instance of the application if you visit 127.0.0.1:8000.

![Github Codespaces 'just' options ](img/screenshot-codespaces-local-environment.png)

### Sharing a view of your environent

Github codespaces allow you to share access to your codespace with other collaborators, or showing your running code, bu sharing it 

- Github documentation on [How to share access to your codespace for pairing and collaboration](https://docs.github.com/en/codespaces/developing-in-a-codespace/working-collaboratively-in-a-codespace)

- Github documentation on [how to make a codespace accessible over specific ports - useful for demonstrating features or designs](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace#sharing-a-port)






---

## Development on a local machine 

The admin-portal project uses the Pyproject format to track software library dependencies, so should work with most python tools for managing dependencies, like `pip`. 

## The supported approach - using `uv` and `just`

With that in mind, the supported, 'golden path' approach is to use the `uv` tool from Astral for managing dependencies, and `just` for automating common tasks.

We recommend and support `uv`, because it helps address many of the common issues managing different versions of Python, both in developmnent and in production, and is actively supported by people working on it full time.

We recommend `just`, as it offers a maintainable way to document and automate common tasks during development. It is both well documented, and actively maintained, and has good support for the use of `.env` files to keep credentials and secrets out of source control.

### Installing just and installing uv

You can install uv with a single one-line command on most systems:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

There are other supported ways to install `uv` documented on Astral's installtion page for the project.


You can also install `just` with a similar one-liner.

```shell
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to DEST
```

### Installing system dependencies

The admin-portal requires a recent version of python, a database compatible with Maria 11, (Mysql can work, but we not actively supported ), and a message queue, currently RabbitMQ. You will need to install these, or run RabbitMQ or Maria DB as a service. There is a docker compose file if you do not want to install them locally.

```
sudo apt install python3 python3-dev build-essential libmariadb3 libmariadb-dev
```

#### Object storage for accessing static files in staging and production

This project relies on object storage in staging and production, to provide redundant storage of upload files. Files are stored with Scaleway object storage. The supported tool for accessing files is [Minio Client](https://min.io/docs/minio/linux/reference/minio-mc.html). Consult the Minio documentation for setting it up to access Green Web object storage where required.


### Working with common tasks

This project uses `just` to provide a convenient way to perform common tasks, and these are defined in `justfile` in the root of the project. Type `just` by itself to see a list of tasks.


#### Running custom tasks with just

You may need to run commands with environment variables set, and with access to the installed python libraries. Use the `just run` command in this case:

```
just run <my-command>
```

Will run my-command with all the environment variables in .env set, and with access to any installed python software, like ansible, dramtiq and so on.


##### Overriding environment variables

If you need to troubleshoot an environment like staging, you can run a command with a different set of environment variables defined. The command below will run `<my-command>` as usual, but using the environment variables defined in a local `.env.staging.local` file instead of the default `.env` file (`.env.staging.local` needs to exist first).

```
just --dotenv-path .env.staging.local run <my-command>
```

## Working with email

```{admonition} Under consideration
:class: todo

We're reviewing if running this as part of the default codespaces docker compose is a good idea.

```

This project has features that send email notifications to users. To test email functionality, this project uses [Mailhog](https://github.com/mailhog/MailHog).

If you need to see emails as they are sent out, and preview their content, open a terminal window and enter the command below to run an instange of Mailhog


```
docker run --rm -p 18025:8025 -p 1025:1025 mailhog/mailhog
```

You should then be able to access the mailhog testing inbox at 127.0.0.1:18025


## Working with Docker

If you prefer working with docker, there are instructions for spinning up a local environment with `docker compose` and building docker images. See [working with docker](working-with-docker.md) for more.
