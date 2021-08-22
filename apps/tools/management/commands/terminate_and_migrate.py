from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def execute(sql):
    """
    Executes the given SQL statement, with optional parameters.
    If the instance's debug attribute is True, prints out what it executes.
    """
    cursor = connection.cursor()

    cursor.execute(sql)

    return cursor.fetchall()


class Command(BaseCommand):
    help = 'Terminate all DB connections and execute `manage.py migrate --all`'

    def handle(self, *args, **options):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if plan:
            self.stdout.write("New migration found\n")
            execute(
                """
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '%s' AND pg_stat_activity.usename = '%s'
            AND pid <> pg_backend_pid() 
            """
                % (settings.DATABASES['default']['NAME'], settings.DATABASES['default']['USER'])
            )
            self.stdout.write("Terminated DB connections\n")
            call_command('migrate', all_apps=True)
            self.stdout.write("All new migrations executed\n")
        else:
            self.stdout.write("No new migrations found\n")
