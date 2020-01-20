# Green Web Foundation

Welcome to the administration system for the Green Web Foundation.

This is the system visible at https://admin.thegreenwebfoundation.org.

It lets staff working for hosting companies update information about how they power the their infrastructure and generates the open datasets we publish each month.

Just here for the datasets? See the [datasets]()

## Installling the project

This is a 2.2 Django project, runnign on MySQL, and is tested on OS X and linux systems.

To install it, create a virtual environment, and install the required librarys

```
python -m venv venv
pip install pipenv
source venv/bin/activate

pipenv install
```

### Credentials

Create a `.env` file where you can store your local secrets or specific settings.

```
DEBUG=on
# DJANGO_SETTINGS_MODULE=myapp.settings.dev
SECRET_KEY='my_useless_development_secret'
DATABASE_URL=mysql://root@localhost:33060/greencheck
```

### Authentication with google for using cloud services

Datasets and backups are stored on Google Cloud storage, and you'll need credentials to access these services if you intend to work on them.

If you work with google cloud storage you need to set environment variable to where it can find the authentication json.

```
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/json/cloud-auth.json"
```

# Deploying

```
pipenv shell
ansible-playbook ansible/deploy.yml -i ansible/inventories/staging
```
