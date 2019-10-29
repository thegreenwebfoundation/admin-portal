# Migrations and stuff

Field that needs to be changed or migrated before we do anything

datacenters.countrydomain - change to max_length 2
datacenters.residualheat - use tinyinteger for boolean
datacenters.virtual - use tinyinteger for boolean
datacenters.dc12v - use tinyinteger for boolean

*in the following order*
hostingprovider.countrydomain - transform com to relevant country
hostingprovider.countrydomain - transform net to relevant country
hostingprovider.countrydomain - change to max_length 2


*making this transformation, will it break current admin?*
hostingproviders.model - transform groeneenergie to green energy
hostingproviders.model - transform compensatie to compensation

hostingproviders.partner - ideally transform null to empty space
