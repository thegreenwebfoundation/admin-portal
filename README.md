Green Web Foundation

**Currently in development**

# Install the project

```
python -m venv venv
pip install pipenv
source venv/bin/activate

pipenv install
```


Create a `.env` file where you can store your local secrets or specific settings. 

```
DEBUG=on
# DJANGO_SETTINGS_MODULE=myapp.settings.dev
SECRET_KEY='my_useless_development_secret'
DATABASE_URL=mysql://root@localhost:33060/greencheck
# REDIS_URL=rediscache://127.0.0.1:6379/1?client_class=django_redis.client.DefaultClient&password=redis-un-githubbed-password

```


# Deploying

```
pipenv shell
ansible-playbook ansible/deploy.yml -i ansible/inventories/staging
```


# Google authentication

If you work with google cloud storage you need to set environment variable to where it can find the authentication json.

```
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/json/cloud-auth.json"
```
