from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Add missing id column for hosting stats."
    TABLE = "hostingproviders_stats"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                START TRANSACTION;
                CREATE TABLE `{self.TABLE}_copy` (
                    `id` INT(11) primary key Not null auto_increment,
                    `id_hp` Int( 11 ) NOT NULL,
                    `green_checks` Int( 11 ) NOT NULL,
                    `green_domains` Int( 11 ) NOT NULL,
                    CONSTRAINT `id_hp` UNIQUE( `id_hp` ) )
                CHARACTER SET = latin1
                COLLATE = latin1_swedish_ci
                ENGINE = InnoDB;
                -------------------------------------------------------------

                INSERT INTO
                    {self.TABLE}_copy(id_hp, green_checks, green_domains)
                SELECT
                    id_hp, green_checks, green_domains
                FROM
                    {self.TABLE};

                DROP TABLE {self.TABLE};
                ALTER TABLE {self.TABLE}_copy RENAME TO {self.TABLE};
                COMMIT;
            """
            )
