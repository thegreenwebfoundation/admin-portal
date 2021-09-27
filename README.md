# Green Web Foundation Admin Portal

Welcome to the administration system for the Green Web Foundation.

This is the system visible at https://admin.thegreenwebfoundation.org.

It lets staff working for hosting companies update information about how they power their infrastructure and generates the open datasets we publish each month.

Just here for the datasets? See the [datasets](https://github.com/thegreenwebfoundation/greenwebfoundation-admin/blob/master/docs/working-with-greenweb-datasets.md)

## Installing the project

This is a 2.2 Django project, running on MySQL, and is tested on OS X and linux systems.

To install it, create a virtual environment, and install the required packages.

```
make venv
. venv/bin/activate
pip install pipenv
pipenv install
```

### Credentials

Create a `.env` file where you can store your local secrets or specific settings.

```
DEBUG=on
# DJANGO_SETTINGS_MODULE=myapp.settings.dev
SECRET_KEY='my_useless_development_secret'
DATABASE_URL=mysql://root@localhost:33060/greencheck
```

Datasets and backups are stored in object storage. You'll need credentials to access these services if you intend to work on them.

See the notes in installation for more.

# Deploying

```
pipenv shell
ansible-playbook ansible/deploy.yml -i ansible/inventories/staging
```
