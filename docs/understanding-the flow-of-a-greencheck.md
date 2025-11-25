# Understanding the life cycle of a Green Check Request

This page outlines the life cycle for the majority of the traffic the Green Web Platform serves - API requests on its greencheck endpoints, most commonly at the following url:

https://api.thegreenwebfoundation.org/greencheck/<DOMAIN>

It exists to inform system design discussions, and help developers new to the system trace a path through the code for common operations.

### When a result has been cached for a domain

When a user carries out a greencheck for a specific site, or a third party uses our greencheck API, you can trace the flow of a request through the system like so:

```{mermaid}
sequenceDiagram

    Browser client->>+Caddy: Look up domain
    Caddy->>+Django Web: Forward to a django web process
    Django Web->>+Database: Look up domain
    Database->>-Django Web: Return lookup result
    Django Web->>+Caddy: Return rendered result
    Caddy->>+Browser client: Present domain result
    Django Web->>+RabbitMQ: Queue domain for logging
```

In most cases we try to find a result we can return quickly, and check in a local cache table called `greendomain`, described by the GreenDomain model. In this case, we return the cached result, and add it to a Rabbit MQ queue, so that a separate worker process can write the check result to a logging table, currently named `greencheck`, and represented by the Greencheck model.

_Note: See the model definitions Greencheck and GreenDomain for the definitive listing of the names the tables we write to - they have changed over time._

Once we have the domain queued, another worker takes the domain off the queue, and logs the checked domain, for later aggregate analysis.

```{mermaid}
sequenceDiagram

    Django Dramatiq->>+RabbitMQ: Check for any domains to log
    RabbitMQ->>+Django Dramatiq: Return domain to log
    Django Dramatiq->>+Database: Log domain to greencheck table
```

The greendomains cache table has a TTL of six months - domains which have not been updated in six months or so are deleted, so that a full check is then carried out on the next lookup.

### When a result has not been cached for a domain (or the cache is requested to be refreshed)

When a domain does not exist in the greendomains table, or we are explicitly refreshing the cache (see below), a full check is carried out, and the result cached to the greendomains table. As above, the check is also added to the rabbitMQ queue, and the check logged asynchronously in the Greencheck table.

The sequence flow diagram looks like so:

```{mermaid}
sequenceDiagram

    Browser client->>+Caddy: Send a request to check a website domain
    Caddy->>+Django Web: Forward to a django web process
    Django Web->>+External Network: Look up domain
    External Network->>+Django Web: Return domain lookup
    Django Web->>+Database: Clear old cached domain lookup from database
    Django Web->>+Caddy: Return rendered result
    Caddy->>+Browser client: Present result for website check
    Django Web->>+RabbitMQ: Queue domain for logging

```
There are two place a cache refresh is always performed:
- **When a manual cache refresh is manually requested** - Either by clicking the "update result" link on the green web checker result page, or by passing the `nocache=true` query parameter on a greencheck API lookup.
- **our own "detail" view for troubleshooting with support** - this is visible at https://admin.thegreenwebfoundation.org/admin/extended-greencheck, and used to show more detail about how we arrive at a given result

### Greencheck images

Greencheck badge images are generated on first request, and cached in object storage, subsequent requests redirect to this existing file rather than regenerating the image. The greencheckbadge endpoint does **not** respect the nocache flag, but a cache busting request to the main greencheck API endpoint will also delete the cached image, allowing it to be updated.
