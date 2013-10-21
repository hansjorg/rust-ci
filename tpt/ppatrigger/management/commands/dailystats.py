import traceback
import pytz
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from ppatrigger.models import Package
from ppatrigger.models import Project
from ppatrigger.models import DailyStats
from ppatrigger.models import Build

class Command(BaseCommand):
    args = ''
    help = 'Compile daily stats for all projects'

    def handle(self, *args, **options):

        packages = Package.objects.all()

        for package in packages:

            self.stdout.write('Creating stats for package ' + str(package))

            latest = None
            try:
                latest_dailies = DailyStats.objects.filter(
                        package__exact = package).order_by('-created_at')

                if len(latest_dailies):
                    latest_daily = latest_dailies[0]
                    latest = latest_daily.created_at
            except DailyStats.DoesNotExist:
                pass

            if not latest:
                # First time running, use package creation
                latest = package.first_created_at
                self.stdout.write('Using package first_created_at: ' + str(latest))
            else:
                self.stdout.write('Using last daily stat created_at: ' + str(latest))

            now = datetime.utcnow().replace(tzinfo = pytz.utc)
            day = latest

            while day <= now: 
                self.stdout.write(str(day) + ' <= ' + str(now))
                next_day = day + timedelta(days=1)

                try:
                    previous_build = Build.objects.filter(fetched_at__lt = day).latest('fetched_at')
                except Build.DoesNotExist:
                    previous_build = None

                if previous_build:
                    previous_version = previous_build.package_version

                builds = Build.objects.filter(
                    project__package__exact = package,
                    fetched_at__gte = day,
                    fetched_at__lt = next_day)

                project_count = Project.objects.filter(
                        created__lt = day).count()

                if len(builds):
                    successful = 0
                    failed = 0
                    errors = 0

                    for build in builds:
                        self.stdout.write(str(build))
                        if build.is_success():
                            successful += 1
                        elif build.is_failure():
                            failed += 1
                        else:
                            errors += 1

                    stats = DailyStats(package = package,
                        date = day,
                        created_at = now,
                        project_count = project_count,
                        successful = successful,
                        failed = failed,
                        errors = errors)

                    stats.save()

                day = next_day
