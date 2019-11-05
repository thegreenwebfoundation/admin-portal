from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "SQL migrations to fit django better."

    def write(self, msg, mode='INFO'):
        if mode == 'INFO':
            self.stdout.write(msg)
        else:
            self.stdout.write(self.style.SUCCESS(msg))

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # comply with the countryfield that we introduced
            cursor.execute(
                "ALTER TABLE datacenters MODIFY countrydomain VARCHAR(2)"
            )

            # Tiny int is enough for boolean fields
            cursor.execute(
                "ALTER TABLE datacenters MODIFY residualheat TINYINT(1)"
            )

            cursor.execute(
                "ALTER TABLE datacenters MODIFY virtual TINYINT(1)"
            )

            cursor.execute(
                "ALTER TABLE datacenters MODIFY dc12v TINYINT(1)"
            )

            cursor.execute(
                "ALTER TABLE greencheck_ip MODIFY active TINYINT(1)"
            )

            # Will truncate a few com and net domains. That are mislabeled in the first place.
            cursor.execute(
                "ALTER TABLE hostingproviders MODIFY countrydomain VARCHAR(2)"
            )

            # Using null in charfield is annoying, an empty string is better
            cursor.execute(
                "UPDATE hostingproviders SET partner = '' WHERE partner IS NULL"
            )

            # change ip fields to integer instead
            cursor.execute(
                "ALTER TABLE greencheck MODIFY ip INT(11)"
            )

            cursor.execute(
                "ALTER TABLE greencheck_ip MODIFY ip_eind INT(11)"
            )

            cursor.execute(
                "ALTER TABLE greencheck_ip MODIFY ip_start INT(11)"
            )

            cursor.execute(
                "ALTER TABLE greencheck_ip_approve MODIFY ip_start INT(11)"
            )

            cursor.execute(
                "ALTER TABLE greencheck_ip_approve MODIFY ip_eind INT(11)"
            )

            # There is no type for year with django, use integer for better compatibility
            cursor.execute(
                "ALTER TABLE greencheck_weekly MODIFY year SMALLINT(5)"
            )
            self.stdout.write(self.style.SUCCESS('Schema migrations completed!'))

            self.stdout.write('Migration passwords to new column')

            try:
                cursor.execute(
                    "ALTER TABLE fos_user ADD COLUMN django_password VARCHAR(128);"
                )
            except Exception:
                self.stdout.write('You ran the migration twice, skipping adding password column')

            cursor.execute("""
                UPDATE fos_user SET django_password = CONCAT('legacy_bcrypt$', password)
                WHERE password LIKE '$2%'
            """)

            self.stdout.write(self.style.SUCCESS('Password migration successful'))

            # make sure that usernames are handled correctly
            cursor.execute("UPDATE fos_user SET username = LOWER(username);")
            try:
                cursor.execute("CREATE UNIQUE INDEX username_unique_index ON fos_user (username);")
            except Exception:
                pass  # index already created

            self.write('Dropping unique index for email_canonical')
            try:
                cursor.execute("DROP INDEX `UNIQ_957A6479A0D96FBF` ON fos_user;")
            except Exception:
                pass  # index already dropped

            self.write('Dropping unique index for username_canonical')
            try:
                cursor.execute("DROP INDEX `UNIQ_957A647992FC23A8` ON fos_user;")
            except Exception:
                pass  # index already dropped

            # Ignore this for now
            # self.stdout.write('Migrating foreign key id_greencheck to be nullable')
            # cursor.execute("""
            #     ALTER TABLE greencheck
            #     MODIFY id_greencheck INT(11) NULL;
            # """)

            # cursor.execute("""
            #     UPDATE greencheck SET id_greencheck = NULL
            #     WHERE id_greencheck = 0;
            # """)

            # self.stdout.write(self.style.SUCCESS('Migrated 0 to be NULL!'))
