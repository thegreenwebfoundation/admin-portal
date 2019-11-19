from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Add missing id column for hostingstats."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.cursor = cursor
            self.cursor.execute('''
                START TRANSACTION;
                CREATE TABLE `hostingproviders_stats_copy` (
                    `id` INT(11) primary key Not null auto_increment,
                    `id_hp` Int( 11 ) NOT NULL,
                    `green_checks` Int( 11 ) NOT NULL,
                    `green_domains` Int( 11 ) NOT NULL,
                    CONSTRAINT `id_hp` UNIQUE( `id_hp` ) )
                CHARACTER SET = latin1
                COLLATE = latin1_swedish_ci
                ENGINE = InnoDB;
                -------------------------------------------------------------

                INSERT into hostingproviders_stats_copy(id_hp, green_checks, green_domains)
                SELECT id_hp, green_checks, green_domains FROM hostingproviders_stats;

                DROP table hostingproviders_stats;

                ALTER table hostingproviders_stats_copy rename to hostingproviders_stats;
                COMMIT;
            ''')
