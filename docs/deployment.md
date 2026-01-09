# Deployment

## Overview

The Green Web Foundation Admin Portal uses GitHub Actions for continuous integration and deployment. The deployment process is automated through a series of reusable workflows that handle testing, permission checks, and deployment to both staging and production environments.


The deployment process is orchestrated through three main workflows:

1. **CI Workflow** (`ci.yml`) - Coordinates testing and deployment
2. **Test Workflow** (`test.yml`) - Runs the test suite
3. **Deploy Workflow** (`deploy.yml`) - Handles deployment to servers



### What is happening with each automated deploy via Github Actions?

The way a Github Actions driven deployment is handled depends on who is making it.

Pull requests from external contributors require manual approval before tests run. Collaborators and owners have tests run automatically, allowing them to get changes into staging or production in one go.

#### Once a workflow starting with tests begins running

Once a decision to run a test made, the tests are run:

**Testing:**
- Tests run in a matrix against Python 3.11 and 3.12
- MariaDB 10.11 and RabbitMQ 3.8 services are automatically started, then the tests run against the services they have exposed.
- Energy consumption for each CI run is tracked with Eco CI

**Deployment:**

Deploys happen upon push to master or staging branches, and they only happen if tests, and a few safety checks pass like checking for pending migrations, or whether there is already an existing deployment in progress.

### Representing this process visually

The (rather imposing) flowchart below is intended to help you trace progress through a deploy triggered by an update to the staging or master branches. 


<details>
<summary>
GitHub Actions Deployment Flow (Click to expand)
</summary>


```{mermaid}
flowchart TD
    Start([Code Push or PR Event]) --> EventCheck{Event Type?}
    
    EventCheck -->|Push to master/staging| PushFlow[Direct Push]
    EventCheck -->|Pull Request| PRFlow[Pull Request]
    
    PushFlow --> IsCollab1[User is Collaborator]
    IsCollab1 --> SetRef1[Set ref to branch]
    
    PRFlow --> CheckCollab{Is Collaborator?}
    CheckCollab -->|Yes| IsCollab2[Collaborator Status]
    CheckCollab -->|No| NotCollab[External Contributor]
    
    IsCollab2 --> SetRef2[Set ref to PR head SHA]
    NotCollab --> SetRef3[Set ref to PR head SHA]
    
    SetRef1 --> TestEnv1[Environment: test]
    SetRef2 --> TestEnv2[Environment: test]
    SetRef3 --> TestEnv3[Environment: test-external]
    
    TestEnv3 --> WaitApproval[Wait for Manual Approval]
    WaitApproval --> RunTests3
    
    TestEnv1 --> RunTests1[Run Test Suite]
    TestEnv2 --> RunTests2[Run Test Suite]
    
    RunTests1 --> Matrix1[Matrix: Python 3.11, 3.12]
    RunTests2 --> Matrix2[Matrix: Python 3.11, 3.12]
    RunTests3[Run Test Suite] --> Matrix3[Matrix: Python 3.11, 3.12]
    
    Matrix1 --> Services1[Start Services:<br/>MariaDB, RabbitMQ]
    Matrix2 --> Services2[Start Services:<br/>MariaDB, RabbitMQ]
    Matrix3 --> Services3[Start Services:<br/>MariaDB, RabbitMQ]
    
    Services1 --> Setup1[Setup Environment:<br/>Python, uv, dependencies]
    Services2 --> Setup2[Setup Environment:<br/>Python, uv, dependencies]
    Services3 --> Setup3[Setup Environment:<br/>Python, uv, dependencies]
    
    Setup1 --> Pytest1[Run pytest]
    Setup2 --> Pytest2[Run pytest]
    Setup3 --> Pytest3[Run pytest]
    
    Pytest1 --> TestResult1{Tests Pass?}
    Pytest2 --> TestResult2{Tests Pass?}
    Pytest3 --> TestResult3{Tests Pass?}
    
    TestResult1 -->|No| Fail1[CI Failed]
    TestResult2 -->|No| Fail2[CI Failed]
    TestResult3 -->|No| Fail3[CI Failed]
    
    TestResult1 -->|Yes| DeployCheck{Push Event?}
    TestResult2 -->|Yes| PRSuccess[PR Tests Passed]
    TestResult3 -->|Yes| PRSuccess2[PR Tests Passed]
    
    DeployCheck -->|No - PR| PRSuccess
    DeployCheck -->|Yes| BranchCheck{Which Branch?}
    
    BranchCheck -->|master| DeployProd[Deploy to Production]
    BranchCheck -->|staging| DeployStaging[Deploy to Staging]
    
    DeployProd --> CheckMigrations1[Check No Pending Migrations]
    DeployStaging --> CheckMigrations2[Check No Pending Migrations]
    
    CheckMigrations1 --> MigrationCheck1{Migrations OK?}
    CheckMigrations2 --> MigrationCheck2{Migrations OK?}
    
    MigrationCheck1 -->|No| MigrationFail1[Deploy Failed:<br/>Run migrations manually]
    MigrationCheck2 -->|No| MigrationFail2[Deploy Failed:<br/>Run migrations manually]
    
    MigrationCheck1 -->|Yes| Serialize1[Serialize Deploy<br/>with turnstyle]
    MigrationCheck2 -->|Yes| Serialize2[Serialize Deploy<br/>with turnstyle]
    
    Serialize1 --> AnsibleDeploy1[Run Ansible: deploy.yml]
    Serialize2 --> AnsibleDeploy2[Run Ansible: deploy.yml]
    
    AnsibleDeploy1 --> AnsibleWorkers1[Run Ansible: deploy-workers.yml]
    AnsibleDeploy2 --> AnsibleWorkers2[Run Ansible: deploy-workers.yml]
    
    AnsibleWorkers1 --> DeployComplete1[Deployment Complete]
    AnsibleWorkers2 --> DeployComplete2[Deployment Complete]
    
    style Start fill:#e1f5ff
    style DeployComplete1 fill:#d4edda
    style DeployComplete2 fill:#d4edda
    style Fail1 fill:#f8d7da
    style Fail2 fill:#f8d7da
    style Fail3 fill:#f8d7da
    style MigrationFail1 fill:#fff3cd
    style MigrationFail2 fill:#fff3cd
    style WaitApproval fill:#fff3cd
```
</details>



## Manual Deployment with Ansible

While deployment is automated via GitHub Actions when pushing to `master` or `staging` branches, you can still deploy manually when needed.

### Standard Deployment Process

The automated deployment (and manual deployment) runs through the following steps:

1. Check Python and Node.js are installed at recent versions
2. Fetch dependencies using `uv` and npm
3. Run build steps to generate static files for Django and frontend pipelines
4. Reload the servers
5. Update caddy/nginx (static files), gunicorn (web requests), and dramatiq (queue workers)

See [ansible/deploy.yml](/ansible/deploy.yml) and [ansible/deploy-workers.yml](/ansible/deploy-workers.yml) for more information.

### When to Deploy Manually

**Database Migrations:** If your code includes database migrations, the automatic deployment will fail with a migration check error. You must deploy manually with migrations.

**Emergency Fixes:** When you need to deploy outside the normal GitHub Actions flow.

**Staging Testing:** To test changes in the staging environment before merging to master.

### Manual Deployment Commands

Assuming you have SSH access set up for the correct servers:

**Standard deployment (no migrations):**
```bash
# Production
just release

# Staging
just release staging

# Or run ansible directly:
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy.yml
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy-workers.yml
```

**Deployment with migrations:**
```bash
# Production
just release_migrate

# Staging  
just release_migrate staging

# Or run ansible directly:
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy.yml
ansible-playbook -i ansible/inventories/prod.yml ./ansible/migrate.yml
ansible-playbook -i ansible/inventories/prod.yml ./ansible/deploy-workers.yml
```

**Important:** The GitHub Actions workflow includes a migration check that will prevent deployment if migrations are pending. This is a safety feature - always run migrations explicitly using `just release_migrate` or the migrate playbook.

### If you need to make changes to how Github actions are set up

The deployment system consists of three coordinated workflows:

#### Main CI Workflow (`.github/workflows/ci.yml`)

The main coordinator that:
- Determines user permissions (collaborator vs external contributor)
- Routes to appropriate test environment
- Triggers deployment for push events to `master` or `staging`

#### Test Workflow (`.github/workflows/test.yml`)

A reusable workflow that:
- Accepts `environment` (test or test-external) and `ref` parameters
- Sets up MariaDB and RabbitMQ services
- Runs pytest against Python 3.11 and 3.12
- Requires approval for external contributors via the `test-external` environment

#### Deploy Workflow (`.github/workflows/deploy.yml`)

A reusable workflow that:
- Accepts `environment` (staging or prod) parameter
- Checks for pending migrations (fails if any exist)
- Uses turnstyle to serialize deployments
- Runs Ansible playbooks against the specified inventory
- Tracks energy consumption with Eco CI

#### Setup Environment Action (`.github/actions/setup-environment`)

A shared composite action that:
- Installs specified Python version
- Installs `uv` for dependency management
- Creates virtual environment and syncs locked dependencies
- Used by both test and deploy workflows


### Note on MyST Markdown Syntax

This documentation uses MyST (Markedly Structured Text) syntax with ` ```{mermaid} ` fences. This is compatible with Sphinx documentation but may not render in the standard VS Code markdown preview without the Mermaid extension.


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

A request comes in, and normally a caddy either serves static files or reverse proxies the request to gunicorn, our django web server. Once the request reaches gunicorn, which is running at least one "worker" process, which actually services the request. Represented visually, it looks like so:

The simplest example

```{mermaid}

flowchart LR

    request[http request]
    request-->caddy
    caddy-->master
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

The logs on each app server are sent to our the Loki server on our monitoring node, accessible at https://grafana.greenweb.org. This allow for centralised querying of logs.
