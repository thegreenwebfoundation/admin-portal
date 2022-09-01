# Working with the Green Web Open Data

Every day The Green Web Foundation publishes a dataset of green domain names, and who hosts them. We call this the `url2green` dataset, and it is available at [datasets.thegreenwebfoundation.org](https://datasets.thegreenwebfoundation.org)

This data closely follows the data available over the Green Web API, and generally speaking, analysis you might use the green web API for, you can use the published datasets for, without needing to hit the API for each check.

## Understanding the url2green dataset

Every check of a website is recorded in a table called `greenchecks`. As of January 2020, this table is nearly 1.6 billion rows, so is rather unwieldy to work with.

For this reason, the dataset we publish contains a smaller table, `green_domains`, listing the urls, and their status, with the columns below.

| Column              |                              Description                               |
| ------------------- | :--------------------------------------------------------------------: |
| _id_                |                        the id of the last check                        |
| _url_               |                            the url checked                             |
| _hosted_by_         |                   the organisation hosting this site                   |
| _hosted_by_website_ |     the website of the company providing the hosting for this site     |
| _partner_           | does this url belong to one of the web green web partner organisations |
| _green_             |              is this a green domain? 1 for yes, 0 for no.              |
| _hosted_by_id_      |                     the id of the hosting company                      |
| _modified_          |            the time and date of the last check of this url             |

## Example uses of this dataset

Because this data provides similar data to the Greencheck API, this dataset can work like an offline cache, where making API calls for each check either would either be too slow, or leak data about your users that you would not want to share.

- _running local checks for privacy_ - a build of the [privacy protecting search engine searx](https://github.com/thegreenwebfoundation/searx/), uses this, to avoid needing to leak information
- _checking domains as part of development workflow_ - tools which consume the green web foundation's green check API, like [Greenhouse](https://github.com/thegreenwebfoundation/lighthouse-plugin-greenhouse), or [Website Carbon](https://websitecarbon.com/), can use this to avoid being reliant on the Green Web API for running checks
- _running analysis to understand how centralisation of the web changes over time_ - because this dataset shows which organisations host each domain, you can get an idea of how the web is becoming more or less centralised, and flowing through fewer providers.

## Licensing of the data

This dataset is releases under the [Open Database Licence](https://opendatacommons.org/licenses/odbl/summary/index.html).

## Getting support with using the the Green Web Foundation datasets

We provide limited, free support for using the Green Web Datasets we publish, and are happy to provide advice or answer questions about this data if you want to use it in classes or research.

If you're interested in further analysis about the shift of the web away from fossil fuels, the Green Web Foundation has data going back to 2009, and we're happy to do collaborations.

Get in touch via [our contact page](https://www.thegreenwebfoundation.org/contact/).
