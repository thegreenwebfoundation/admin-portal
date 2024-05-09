import os

# Refer to gunicorn settings below for more info on each one
# https://docs.gunicorn.org/en/stable/settings.html
timeout = 300
# increasing workers uses more RAM, but provides a simple model for scaling up resources
workers = os.getenv("GUNICORN_WORKERS", default=8)
# increasing threads saves RAM at the cost of using more CPU
threads = os.getenv("GUNICORN_THREADS", default=1)

# Log HTTP requests, so we can compare them with our reverse proxy
accesslog = "-"
# use the default log format, but add the time taken by each request in milliseconds as well %(M)s
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(M)s "%(f)s" "%(a)s"'

# set gunicorn log level to info, not warning.
loglevel = "info"
# capture the output from django, to pipe to the gunicorn errlog
capture_output = True
