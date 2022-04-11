# Installation

This installation shows you how to setup the Admin Portal of The Green Web Foundation.<br>
In order to setup this project, we recommend following the guides from top to bottom. Skipping some topics might result in missing crucial steps for the project to work.

---
## Gitpod
### Why Gitpod
To speed up and simplify the installation process, we use Gitpod. <br> We strongly recommend using this tool.
 
### Preparing a Gitpod workspace
After logging into Gitpod or creating an account we recommend also installing the Gitpod browser extension. This extension integrates extra functionality in websites such as Github.

1. Go to our [Github repository](https://github.com/thegreenwebfoundation/admin-portal) and click on the Gitpod button if you have the browser extention installed or manually create and link it in your Gitpod Workspaces. It might take a couple of minutes to prepare the environment.
2. After Gitpod is finished preparing the environment, it will open the workspace. Close any unnecessary terminal windows. To open a new fresh terminal window press ```Ctrl + ` ```.
---
## Virtual environment
In an isolated virtual environment we are able to act on various usefull tools within the project.

### Setup
Before following the following list, make sure you are in the root directory (workspace/admin-portal).
1. Start by creating a virtual environment named *venv* by executing the following command in a terminal window: ```make venv```.
2. Now that the environment has been created, we can access it with the following command ```. venv/bin/activate```.
3. Download a packages named *pipenv* with *pip*: ```pip install pipenv```.
4. Once download, use this tool to install all other packages: ```pipenv install```.
5. As a final step, make sure to copy the content of ```.env.sample``` to ```.env``` and add the necessary credentials.<br>
__Note__ that this project relies on object storage. In production this is needed to store static files, but in development it is not required.

By default ```pipenv``` loads the content of the ```.env``` file.<br>
For starting the project the shell command can be used like this ```pipenv shell```. 