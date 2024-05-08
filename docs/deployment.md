# Deployment

### Github conventions

....

### Using Ansible

We use Ansible to deploy versions of the site to our servers.

More specifically, when we merge into the main/master branch, it triggers a deploy to production automatically, running the `deploy` playbook.

This runs through the following steps:

- check python and nodejs installed at recent versions
- fetch dependencies for both cases
- run build steps to generate static files for django and any artefacts needed in front end pipelines
- reload the servers
- if necessary, update caddy/nginx (for static files and webserver), gunicorn (for serving web requests), or dramatiq (for our queue and workers)

See `deploy.yml` and `deploy-workers.yml`, for more information.

Assuming you have ssh access set up for the correct servers, you deploy with the following command:

```
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy.yml
```

Alternatively, merging code into master triggers the same ansible script via github actions.

### Understanding our infrastructure

Broadly speaking, the green web platform is deployed onto a set servers that are kept under config management, using a combination of Ansible for mainly provisioning VMs, and Nomad for scheduling the jobs run on these VMs.

See the [staff-only private github repository for more](https://github.com/thegreenwebfoundation/infra/), and if you have access see [the infrastructure tag on the team trello board](https://trello.com/b/Y3FFGswA/green-web-platform-change-work).


#### Other relevant links:

- [Google doc design document for making recent infrastructure updates](https://docs.google.com/document/d/1GeifHzEdmPUvqectFYK3jrWSvLI0UqwbQ7j2sT7tSwQ/edit#heading=h.5vcjqio8w4vn)
- [Our Grafana instance for tracking metrics, and logs](https://grafana.greenweb.org)
- [Our Nomad instance, which shows the state of most scheduled services and jobs](https://nomad.greenweb.org)







Access to the servers, and wider config maintained using a set of ansible scripts in a private github repository


### how our web servers are deployed

The chart below outlines a high level model of how different moving parts serve web requests.

A request comes in, and normally a nginx either serves static files or reverse proxies the request to gunicorn, our django web server. Once the request reaches gunicorn, which is running at least one "worker" process, which actually services the request. Represented visually, it looks like so:

The simplest example

```{mermaid}

flowchart LR

    request[http request]
    request-->nginx
    nginx-->master
    master

    subgraph gunicorn
        master-->worker1
        subgraph worker1[worker ]
            %% render left to right
            %% to make them stack
            direction LR
        end
    end
```

One gunicorn master procss with one worker will not be able to serve that many requests by itself, so in production we use multiple workers.

Gunicorn allows us to use multiple types of workers, to fit the workload we are serving, and the resources we have available, like available RAM, free cores, and CPU cycles.

For a workload where we have free RAM, and CPU, we'd serve 4 sync workers, like so.

#### A model closer to production - 4 sync workers

```{mermaid}
flowchart LR

    request
    request-->master

    subgraph gunicorn

        master-->worker1
        master-->worker2
        master-->worker3
        master-->worker4

        subgraph worker1[worker 1]
        end

        subgraph worker2[worker 2]
        end

        subgraph worker3[worker 3]
        end

        subgraph worker4[worker 4]
        end

    end


```

Where ram is constrained, but we have spare CPU capacity, and work is IO bound, we can allocate multiple threads within a worker. This allows a single worker to serve multiple requests, and the threads within a worker are sharing memory, we can still serve multiple requests, without needing to allocate so much memory:

#### 2 workers, each with 2 threads

```{mermaid}
flowchart LR

    request
    request-->master

    subgraph gunicorn

        master-->worker1
        master-->worker2

        subgraph worker1[worker 1]
            %% render left to right
            %% to make them stack
            direction LR
            thread1
            thread2
        end

        subgraph worker2[worker 2]
            %% render left to right
            %% to make them stack
            direction LR
            thread3
            thread4
        end

    end
```


As the workloads we serve change, we may need to update the numbers of workers and the kinds of workers,to make the best use of the resources available to serve the workloads facing us. See "scaling processes" below for more

**See the code**

Run the code below from the project root, to run gunicorn:

```
# run gunicorn using the `greenweb.wsgi` for defining the behavior inside django,
# the file `gunicorn.conf.py` to define gunicorn's behaviour,
# and binding to port 8000 of the network address 0.0.0.0
gunicorn greenweb.wsgi --bind 0.0.0.0:8000 -c gunicorn.conf.py
```

See `gunicorn.conf.py` in the code base for further informatinon about the workers in use, and `greenweb/wsgi.py` to see which django config file is used to define how the django application behaves.

**Further reading**

1. [More on using 'sync' gunicorn workers compared to other types](https://hackernoon.com/why-you-should-almost-always-choose-sync-gunicorn-over-workers-ze9c32wj)
2. [Different means of acheiving concurrency with gunicorn](https://medium.com/building-the-system/gunicorn-3-means-of-concurrency-efbb547674b7)
3. [Using the univorn.worker class to serve async requests with Gunicorn](https://www.uvicorn.org/deployment/)

### Workers

We use dramatiq to handle out of band requests, for actions that will take longer than we would like a user to wait to receive a response.

Here use rabbit MQ as our queue system, and Dramatiq for managing workers. Dramatiq relies on an actor model for picking up work on a queue, and allocating enough workers.

If you have a series of very heavy, computationally expensive jobs in the queue, there is a risk that all the workers will be stuck working on these, as lots of smaller jobs pile up.

To avoid this, we have multiple queues - regular, fast finishing throughput work is allocated to the _default_ queue. Heavier, batch processing work to generate stats should be allocated to the stats_ queue.

#### Typical queue operation - serving fast and slow responses

```{mermaid}
flowchart LR

    subgraph dramatiq
        worker[worker ]
        worker2[worker 2]
        worker3[worker 3]
        worker4[worker 4]

    end

    subgraph rabbitmq
         %% render left to right
         %% to make them stack
         direction LR
         default
         stats
     end

    worker-->default
    worker2-->default
    worker3-->default
    worker4-->stats
```

You can run a worker jobs with the following command:

```
# serve one worker, using one thread per worker, just for the default queue
manage.py rundramatiq --threads 1 --processes 1 --queues default

# serve one worker, using one thread per worker, just for the stats queue
manage.py rundramatiq --threads 1 --processes 1 --queues stats

# serve the default: as many workers as cores available, each with 8 threads, for all queues
manage.py rundramatiq
```

Update the number of threads and processes accordingly to allocate the appropriate amounts of resources for the workloads.

### Scaling processes with ansible

Each new deploy using the `deploy.yml` ansible playbook deploys the version of the branch specified in `project_deploy_branch`, including number of processes for both the gunicorn web server and for the dramatiq queue workers.

If you only want to scale the workers up and down, and don't want to run through the whole deployment process, updating just the processes is possible.

You have two possible options - first pass the `systemd` tag to the deploy script. This will only run the steps tagged with `systemd` in the deploy playbook.

```
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy.yml --tags systemd
```

Alternatively, you can run the dedicated `scale-processes.yml` playbook. This includes the same tasks as are defined in the larger `deploy` playbook:

```
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy.yml --tags systemd
```

These playbooks template out new scripts that systemd uses to run both the gunicorn web servers and dramatiq queue workers, then send a command to update stop, start or restart these processes.


**Further reading**

1. [The dramatiq guide](https://dramatiq.io/guide.html)
2. [Django Dramatiq, the pacakge we use for interfacing with dramatiq](https://github.com/Bogdanp/django_dramatiq)


### Logging

As mentioned before, we use systemd to run our both our workers and web server processes. This means processes are restarted automatically for us, and logs are rotated for us.

### Gunicorn logging

By default, gunicorn, our web server logs at the `INFO` level. This means successful requests are not logged, and only errors (with the status code 5xx) or not found requests (4xx)  show up in logs.

The logs on each app server are sent to our the Loki server on our monitoring node, accessible at https://grafana.greenweb.org. This allow for centralised querying of logs.
