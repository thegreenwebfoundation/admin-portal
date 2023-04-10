4# Understanding checks for green sites

It's worth referring to the general principle we apply when checking if a site or a services from a digital provider is green:

> If you want a green site, you need to demonstrate steps you are taking to avoid, reduce or offset the greenhouse gas emissions caused using electricity to provide the service. You need to do this on a yearly basis, or better.

The two main ways we track this being done are either running a service powered by green energy, or using a service from a provider using green energy. You can [read more about what we class as green energy and what evidence we required on our main site][1] - this content explains how we establish the link between a site and the supporting evidence linked to a given service.

[1]: https://www.thegreenwebfoundation.org/what-we-accept-as-evidence-of-green-power/

## Making this more specific

More concretely, when we do a check for a site, we are usually looking up a domain like `mycoolsite.com`, then resolving that to an IP address. Once we have the IP address, we check it against a set of IP ranges or Autonomous System networks (ASN) that are associated with a given provider that we have supporting evidence for. We outline each approach below.

Once we the IP address, we take one of three paths to arrive at an organisation that we have information for.

1. Domain, to IP to provider, by IP range
2. Domain to IP to provider, by ASN
3. Domain to carbon.txt lookup, to provider(s)

We'll cover each one in turn.

### Domain, to IP to provider, by IP range

Once we have an IP address, we establish the link a provider by checking if this IP falls inside one of the IP ranges already shared with us by a given service provider.

#### Linking directly to a provider by IP range

So, if an IP address is `123.123.123.100`, and we have an IP range for Provider A, who has registered the IP range `123.123.123.1` to `123.123.123.255`, we associate the lookup with that provider, and refer to the supporting evidence shared with us by Provider A.

This is the simplest case - where a domain might be `provider-a.com`, resolving to the IP address, which we then link to Provider A, the organisation.

#### Linking a site to a provider in the site's supply chain

There will be cases where an organisation isn't running its own servers or other infrastructure itself, but instead of using a service from a green provider. Historically, this has been the most common scenario, because one hosting provider will typically host lots of websites on behalf of other organisations.

In this case a domain might be `my-cool-site.com`, which resolving to the IP address, which we then link to Provider A, the organisation.


### Domain, to IP to provider, by ASN

For some larger providers, maintaining a register of every single IP Range with the green web foundation can be cumbersome, so we also support lookups by Autonomous System Network (ASN) instead.

There are millions of IP addresses in the world, but the internet is a big place, and they are not infinite. An organisation called the Internet Assigned Numbers Authority, IANA allocates these blocks of IP ranges to _regional internet registries_, who then allocate them either to organisations for use directly, or to smaller, _local internet registries_ who then allocate them to organisations like _internet service providers_, (ISPs) or companies using them directly themselves.

Maintaining which individual IP address points to which is something that is often better managed at the local level, and the internet itself made of up tens of thousands smaller networks called Autonomous Systems Networks, that manage this themselves.

If we don't have a matching range for an IP address, we can perform a lookup to see which AS Network the IP address belongs to - if an entire AS network belongs to one organisation, and we have supporting evidence for the organisation using enough green energy, this saves duplicating the records that the AS network is managing themselves.

As before, we support two cases - an organisation providing a digital service themselves, or an organisation using a green provider to provide a service.

#### Linking directly to a provider by ASN

In this case, a domain might be `provider-b.com`, resolving to the IP address `231.231.231.231`. From there we perform a lookup to find Autonomous Network 12345 (`AS 12345`), which is owned exclusively by `Provider B`, the organisation, and has been registered with us.

By following the link to supporting evidence shared by `Provider B`, we can establish the link to green energy.

#### Linking a site to a provider in the site's supply chain

Similarly, a domain `my-green-site.com`, which resolves to the IP address `213.213.212.213`. From there, we perform a lookup to the same Autonomous Network 12345 (`AS 12345`). We follow the link from `AS 12345` to link to Provider B, and refer to their evidence to establish the link to green energy.

------

### Domain to carbon.txt lookup

The final supported approach, which is currently under development, is to avoid relying on IP addresses entirely, and go straight from a domain name, to one or more providers, based on machine readable information exposed in a `carbon.txt` file.


The flow is as follows:

1. Check the domain name is a valid one.
2. Check there if there is `carbon-txt` DNS TXT record for the given domain.
3. Perform an HTTP request at https://domain.com/carbon.txt, OR the overide URL given as the value in the DNS TXT lookup.
4. If there is valid 200 response and a parseable file, parse the file.
5. If there is a no valid 200/OK response at domain.com/carbon.txt (i.e. a 404, or 403), check the HTTP for a `Via` header with a new domain, as a new domain to check.
6. Repeat steps 1 through 5 until we end up with a 200 response with a parsable carbon.txt payload, or bad request (i.e. 40x, 50x).

Once there is a parseable carbon.txt file, the domain the carbon.txt belongs to is used as a lookup key against a known list of domains associated with a provider. If there is a match, the site is assumed to be running at the provider, and shows as green.

#### Why do it this way?

This flow is designed to allows CDNs and managed service providers to serve information in a default carbon.txt file, whilst allowing "downstream" providers to share their own, more detailed information if need be.

**Why support the carbon.txt DNS TXT record?**

Supporting the DNS lookup allows an organisation that owns or operates multiple domains to refer to a single URL for them to maintain.
The "override URL" also allows for organisations that prefer to serve their file from a `.well-known` directory to do so, without explicitly requiring it from people who do not know what a `.well-known` directory is, or want to control who is able to write to the directory.

**Why use the `Via` header?**

Consider the case where a managed-service-provider.com is hosting customer-a.com's website.

The managed service provider may be  offering a CDN or managed hosting service, but they may not have control over the customer-a.com domain. They may not have, or want direct control over what a downstream user is sharing at a given url. However because they are offering some service "in front" of customer-a's website, and serving it over a secure connection, they are able to add headers to HTTP requests.

the [HTTP Via header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/via) exists specifically to serve this purpose, and provides a well specified way to pass along information about a domain of the organisation providing a managed service, when the domain is different.

**Why use domain/carbon.txt as the path?**

Defaulting to a root `carbon.txt` makes it possible to implement a carbon.txt file without needing to know about `.well-known` directories, that by convention are normally invisible files. Having a single default place to look avoids needing to support a hierarchy of potential places to look, and precedence rules for where to look - there is either one place to default to when making an HTTP request, OR the single override.


**How can you trust this? What would stop me lying in my carbon.txt file about my site?**

You could indeed list a green provider in your supply chain, and claim it was hosting your site, so your site showed up as green through association. Your site would not show up as green until you had been able to submit some supporting evidence for manual review that you _really were_ using that provider.

After manual review by our support staff, you would have managed to mark one domain as green.


**What would stop me using someone else's carbon.txt file instead?**

There are two mechanisms designed to mitigate against lying.

**1. Manual review for new domains** - just like with your own domain, we have a manual review step for any new domain delegating to one already trusted. New domains don't show as green until they have been added to an allow list for a given provider, or until a domain hash is made available when performing a lookup. More on domain hashes below.

**2. Domain hashes for newly seen domains** -

Domain hashes are SHA256 hashes based on:

1. the domain a lookup is being delegated to
2. a secret shared that only the green web platform and the provider associated with the domain above has access to

They are an optional part of either a TXT record or HTTP header, when delegating a lookup to carbon.txt file at a different domain. They allow the organisation Cool Green Hosted Services Inc, who own the domain cool-green-hosted-services.com, and who are serving a site at domain customer-of-green-hosted-services.com, to assert that it's really organisation Cool Green Hosted Services Inc operating the infrastructure powering customer-of-green-hosted-services.com, and to use the supporting evidence shared by Cool Green Hosted Services Inc, for any green checks.



For more, please follow the link to the [github repo where the syntax and conventions are being worked at out](https://github.com/thegreenwebfoundation/carbon.txt).
