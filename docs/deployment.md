## Deployment

```{admonition} Draft
As a ... you probably want to deploy your work at some point. The following steps will guide you through the process of deploying your work.
```

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
- if necessary, update nginx

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
