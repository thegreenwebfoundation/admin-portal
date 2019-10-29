Green Web Foundation

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
