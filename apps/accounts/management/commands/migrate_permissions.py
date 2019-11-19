import re

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from apps.accounts.models import User

role_re = re.compile(r'"(ROLE_\w+)"')
GROUPS = {
    'ROLE_ADMIN': Group.objects.get_or_create(name='admin'),
    'ROLE_HOSTINGPROVIDER': Group.objects.get_or_create(name='hostingprovider'),
    'ROLE_DATACENTER': Group.objects.get_or_create(name='datacenter'),
    'ROLE_LINX': Group.objects.get_or_create(name='linx'),
    'ROLE_GREENENERGY': Group.objects.get_or_create(name='green_energy')
}


class Command(BaseCommand):
    help = "Migrate all user permissions to groups."

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            match = role_re.search(user.roles)
            if not match:
                continue

            roles = match.groups()
            for role in roles:
                group, created = GROUPS[role]
                user.groups.add(group)
                if role == 'ROLE_ADMIN':
                    user.is_staff = True
                    user.is_superuser = True
                user.is_active = True
                user.save()
        self.stdout.write(self.style.SUCCESS('Migrating permissions completed!'))
