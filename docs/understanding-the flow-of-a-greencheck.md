# Understanding the life cycle of a Green Check Request

This page outlines the life cycle for the majority of the traffic the Green Web Platform serves - API requests on it's greencheck endpoints.

It exists to inform system design discussions, and help developers new to the system trace a path through the code for common operations.

### Our usual, fast check

When a user carries out a greencheck for a specific site, or a third party uses our greencheck API, you can trace the flow of a request through the system like so:

```{mermaid}
sequenceDiagram

    Browser client->>+Nginx: Look up domain
    Nginx->>+Django Web: Forward to a django web process
    Django Web->>+Database: Look up domain
    Database->>-Django Web: Return lookup result
    Django Web->>+Nginx: Return rendered result

    Nginx->>+Browser client: Present domain result
    Django Web->>+RabbitMQ: Queue domain for logging
```

In most cases we try to find a result we can return quickly, and check in a local cache table, described by the GreenDomain model. Assumign we find a result in the database, we put the checked domain on a Rabbit MQ queue, so that a separate worker process can update to the cache to record the time of the check, and so it can write the check result to a logging table.


### Updating our green domains table

Once we have the domain queued, another worker takes the domain off the queue, and does two things.

1. It updates our green domain table that has been acting like our cache, so we can easily see which domains lookups are the 'freshest'.
2. It then logs the checked domain, for later aggregate analysis.

It also lets us control the load we place on the database by controlling when we are logging all the checks, as well as updating our cache table.

```{mermaid}
sequenceDiagram

    Django Dramatiq->>+RabbitMQ: Check for any domains to log
    RabbitMQ->>+Django Dramatiq: Return domain to log
    Django Dramatiq->>+Database: Log domain to greencheck table
    Django Dramatiq->>+Database: Update greendomain tables
```

We can scale the two of these independently, depending on the traffic we are receiving, and RabbitMQ here acts like a buffer.

### Carrying out a slow full network look up

We also have a slower check that does all of this in one synchronous request - here we prioritise accuracy over response time, and skip any lookup against a local cache table. We still log the check for a worker to pull off the queue, and to update the green domain cache as usual, but this allows us to always show the result from a full network look up in case we suspect that the result in our cache table is stale.

The sequence flow diagram looks like so:

```{mermaid}
sequenceDiagram

    Browser client->>+Nginx: Send a request to check a website domain
    Nginx->>+Django Web: Forward to a django web process
    Django Web->>+External Network: Look up domain
    External Network->>+Django Web: Return domain lookup
    Django Web->>+Database: Clear old cached domain lookup from database
    Django Web->>+Nginx: Return rendered result

    Nginx->>+Browser client: Present result for website check
    Django Web->>+RabbitMQ: Queue domain for logging

```
