### Recurring tasks on the Green Web Platform

The Green Web Foundation platform relies on a number of regular tasks run by scripts, that happen on a daily, or weekly basis.

To make it easier to maintain and track configuration drift (i.e. small changes in leading to unexpected behaviour), these are kept in source control as role and playbooks in Ansible.


```{admonition} Draft
A number of these cronjobs were set up manually before by green web foundation staff. As these jobs are moved under configuration management in source code they will be added to the documentation here.
```

### Weekly imports

While the Green Web Foundation offers a self-service way to maintain up to date lists of IP ranges and AS numbers, historically we maintained a set of automated importers of IP ranges for a small number of large providers of hosted services. These providers who publish their IP ranges in a machine-readable format at public endpoints our systems can access, then import into the corresponding provider's lists of AS numbers and IP ranges. 

These can be run on the command line using the following commands

```
pipnev run ./manage.py update_networks_in_db_amazon
pipnev run ./manage.py update_networks_in_db_google
pipnev run ./manage.py update_networks_in_db_microsoft
```

Look in the `import_ips_for_large_providers.sh.j2` file to see the specific shell script run each week, and the `setup_cronjobs.yml` ansible playbook to see the specific tasks used to set up a a server to run these on a recurring schedule.

#### Defining the cronjob

Using 

```yaml
- name: Ensure job to run IP hyperscaler importers is present
  ansible.builtin.cron:
    name: "every Wednesday at 4:30 run our importers"
    state: present
    weekday: "WED"
    hour: "4"
    minute: "30"
    user: deploy
    job: >
      bash /home/deploy/cronjobs/import_ips_for_large_providers.sh 
      >> /var/log/import_ips_for_large_providers.log 
      2>> /var/log/import_ips_for_large_providers.error.log
  tags: [crontab]
```

Here in this snippet of ansible code, we run a script, each week, and we pipe the output into a dedicated log file (see `>> /var/log/import_ips_for_large_providers.log`), along with piping any errors into a dedicated error log file (see the `2>>` part to pipe STDERR into `/var/log/import_ips_for_large_providers.error.log`).

We use the yaml folded scalar literal to make the formatting easier to read, along with the time we want the job to run.

#### Checking that the cronjobs are on the server

If you wanted to check that a cronjob is set up on the necessary server, you would run the following ansible command, passing in the correct inventory file to tell ansible which set of servers to connect to, and passing in `--check`` to see what changes might take effect:

```
pipenv run ansible-playbook -i ansible/inventories/prod.yml ansible/setup_cronjobs.yml --check
```

To run the actual command, and update the cronjobs, you would run the same command, without the `--check` flag.

```
pipenv run ansible-playbook -i ansible/inventories/prod.yml ansible/setup_cronjobs.yml
```

### Daily Green Domain Exports

In addition to offering the greencheck API, we create regular exports of the green domains table as compressed sqlite files, available in object storage.

These are intended for cases when hitting an external API is either impractical, or in places where privacy is a higher priority, avoiding making network requests that show which domain is being checked.

This export is normally run with the following django management command.

```
pipenv run ./manage.py dump_green_domains
```

To upload the database snapshot to object storage, pass long the `--upload` flag.


```
pipenv run ./manage.py dump_green_domains --upload
```

This is currently set to run every day, but historically, this job not run consistently every single day.

There is ongoing work to backfill these domains for the missing days
