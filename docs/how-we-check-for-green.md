# Understanding checks for green sites

It's worth referring to the general principle we apply when checking if a site or a services from a digital provider is green:

> If you want a green site, you need to demonstrate steps you are taking to avoid, reduce or offset the greenhouse gas emissions caused using electricity to provide the service. You need to do this on a yearly basis, or better.

The two main ways we track this being done are either running a service powered by green energy, or using a service from a provider using green energy. You can [read more about what we class as green energy and what evidence we required on our main site][1] - this content explains how we establish the link between a site and the supporting evidence linked to a given service.

[1]: https://www.thegreenwebfoundation.org/what-we-accept-as-evidence-of-green-power/

## Making this more specific

More concretely, when we do a check for a site, we are usually looking up a domain like `mycoolsite.com`, then resolving that to an IP address. Once we have the IP address, we check it against a set of IP ranges or Autonomous System networks (ASN) that are associated with a given provider that we have supporting evidence for. We outline each approach below.

Once we the IP address, we take one of three paths to arrive at an organisation that we have information for.

1. Domain to provider, by an explicitly _Linked Domain_ (verified with [carbon.txt](https://carbontxt.org)).
2. Domain, to IP to provider, by IP range
3. Domain to IP to provider, by ASN

We'll cover each one in turn.

### Domain to provider, via a Linked Domain.

The first check we carry out, is whether the domain has been explicitly "linked" to a provider within our platform by the provider itself, using a [carbon.txt](https://carbontxt.org) file.

This is a simple database query at the point the query is made, but the process of registering (and validating) a linked domain is more involved:

The flow is as follows:

1. The provider [implements carbon.txt for their domain](https://carbontxt.org/quickstart), either by uploading a carbon.txt file to the site directly, or delegating to another domain or URL with a DNS TXT record or HTTP header.
2. The provider registers the linked domain in the provider portal
3. The carbon.txt file is automatically checked on registration - [ADR 2](https://github.com/thegreenwebfoundation/carbon-txt-validator/blob/main/docs/adrs/02_improvements_to_delegation_and_domain_validation.md) and [ADR 3](https://github.com/thegreenwebfoundation/carbon-txt-validator/blob/main/docs/adrs/03_change_of_lookup_priority_order.md) in the carbon.txt project give full details of how this check is implemented.
4. If the carbon.txt lookup resolves and the resulting file is syntactically valid, the linked domain is set up in a "Pending review" state - GWF staff then manually verify that this domain corresponds to the given provider, and approve the linked domain if so.
5. Once a linked domain is approved, it will be used as the first step in any green domain check, ensuring that the linked provider is always shown for that domain.

#### Why do it this way?

This flow is designed to allows CDNs and managed service providers to serve information in a default carbon.txt file, whilst allowing "downstream" providers to share their own, more detailed information if need be. This provides important benefits for two different groups of users:

- Hosting providers who resell infrastructure for another provider
- Anyone using a CDN (eg cloufront, cloudflare) in front of their own infrastructure

Both of these groups of users would *not* be shown as the corresponding provider in a greencheck using only IP or ASN based checks - the ability to explicitly link a domain to a provider allows us to ensure the correct provider is listed in a verified manner.


**How can you trust this? What would stop me lying in my carbon.txt file about my site?**

You could indeed list a green provider in your supply chain, and claim it was hosting your site, so your site showed up as green through association. Your site would not show up as green until you had been able to submit some supporting evidence for manual review that you _really were_ using that provider.

After manual review by our support staff, you would have managed to mark one domain as green.

**What would stop me using someone else's carbon.txt file instead?**

**1. [Current approach] Manual review for new domains** - just like with your own domain, we have a manual review step for any new domain delegating to one already trusted. New domains don't show as green until they have been added to an allow list for a given provider. We are in the process of replacing this with an automated verification process, based on _domain hashes_:

**2. [To be implemented] Domain hashes for newly seen domains** -

Domain hashes are SHA256 hashes based on:

1. the domain a lookup is being delegated to
2. a secret shared that only the green web platform and the provider associated with the domain above has access to

They are an optional part of either a TXT record or HTTP header, when delegating a lookup to carbon.txt file at a different domain.

They allow the organisation *Cool Green Hosted Services Inc*, who own the domain `cool-green-hosted-services.com`, and who are serving a site for a customer *Customer Of Green Hosted Services Ltd* at domain `customer-of-green-hosted-services.com`, to assert that it's really organisation *Cool Green Hosted Services Inc* operating the infrastructure powering `customer-of-green-hosted-services.com`. This allows them to use the supporting evidence shared by
*Cool Green Hosted Services Inc*, for any green checks by default.

Once they are implemented, an extra step will be added to the linked domain registration process above: After the carbon.txt has been resolved and syntactically verified, the hosting provider will be directed to add a `gwf-domain-hash` DNS TXT record or `GWF-DomainHash` HTTP header containing this SHA256 hash, and the authenticity of the record will be verified before proceeding to create the linked domain. This both provides stronger guarantees of domain ownership than manual review, and results in a simpler, faster process.

For more, please follow the link to the [github repo where the syntax and conventions are being worked at out](https://github.com/thegreenwebfoundation/carbon.txt), and in particular [ADR 2](https://github.com/thegreenwebfoundation/carbon-txt-validator/blob/main/docs/adrs/02_improvements_to_delegation_and_domain_validation.md).

### Domain, to IP to provider, by IP range

If no Linked Domain exists for the given domain, we proceed to the IP based check.

The domain is resolved to an IP address using the standard DNS mechanism.

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

