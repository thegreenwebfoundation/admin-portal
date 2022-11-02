# The Green Web Foundation Public APIs

Since 2006, we have been building the world’s largest database tracking which parts of the internet run on renewable power, and when they switched. That's a lot of data, and we believe strongly in making it freely available for use in projects, reporting, and academic research. To make this possible, we have created a set of public APIs.

## What's in this folder?

In this document, you will find:

- [List of available APIs](#available-apis)
- [Links to API documentation](#api-documentation)
- [Source code for The Green Web Foundation's public APIs](#source-code)
- [Links to the data behind the APIs](#green-domains-dataset)

## Available APIs

We make available the following public APIs:

- **IP to CO2 Intensity**: Query a public IP address, and receive information about that IPs location (country) as well as annual average grid intensity data.
- **Greencheck**: Query a website domain, and receive information whether that site is hosted on a certified green web host.
- **Directory**: Query The Green Web Foundation's database of certified green hosting providers.
- **IP Range**: Query the known IP ranges and their associated providers.
- **AS Network**: Query the known AS Networks and their associated providers.

## API documentation

All API endpoints are documented using the Open API specification at https://api.thegreenwebfoundation.org/api-docs/

### New documentation portal

We are gradually moving all documentation for our developer-facing code and APIs to  https://developers.thegreenwebfoundation.org/. This website provides a more approachable, user friendly experience for people new to our open-source tooling.

Currently the following APIs are documented there:

- [IP to CO2 Intensity](https://developers.thegreenwebfoundation.org/api/ip-to-co2/overview/)
- [Greencheck](https://developers.thegreenwebfoundation.org/api/greencheck/v3/check-single-domain/)

## Source code

The core source code for all API endpoints can be found in [/models/checks.py](/apps/greencheck/models/checks.py).

Views (endpoint routes) are all declared in [/api/views.py](/apps/greencheck/api/views.py).

## Green Domains Dataset

The Green Domains Dataset powers the Greencheck API. It  is a browseable daily snapshot all the green domains tracked in the Green Web Foundation database, along with who they are hosted by, and when they were last updated. You can also download a snapshot or full dump of the data should you need to.

https://datasets.thegreenwebfoundation.org/

