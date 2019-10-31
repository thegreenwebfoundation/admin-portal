# Migrations and stuff

Field that needs to be changed or migrated before we do anything

datacenters.countrydomain - change to max_length 2

datacenters.residualheat - use tinyinteger for boolean
datacenters.virtual - use tinyinteger for boolean
datacenters.dc12v - use tinyinteger for boolean
greencheck_ip.active - use tinyinteger for boolean

*in the following order*
hostingproviders.countrydomain - transform com to relevant country
hostingproviders.countrydomain - transform net to relevant country
hostingproviders.countrydomain - change to max_length 2


*making this transformation, will it break current admin?*

hostingproviders.partner - ideally transform null to empty space

greencheck.ip - change to integer field
greencheck_ip.ip_eind - change to integer field 
greencheck_ip.ip_start - change to integer field

greencheck_ip_approve.ip_eind - change to integer field 
greencheck_ip_approve.ip_start - change to integer field

greencheck_weekly.year - make it a smallintegerfield instead. 


# Still need to write script for these

migrate roles of users to groups.

hostingproviders.model - transform groeneenergie to green energy
hostingproviders.model - transform compensatie to compensation

# Passwords

write a migration to amend all password hashes with `legacy_bcrypt$`
