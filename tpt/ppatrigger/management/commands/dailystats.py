import traceback
import pytz
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from ppatrigger.models import Package
from ppatrigger.models import DailyStats
from ppatrigger.models import Build

class Command(BaseCommand):
    args = ''
    help = 'Compile daily stats for all projects'

    def handle(self, *args, **options):

        packages = Package.objects.all()

        for package in packages:

            try:
                latest_daily = DailyStats.objects.filter(
                        package__exact = package).earliest('created_at')

                latest = latest_daily.created_at
            except DailyStats.DoesNotExist:
                # First time running, use package creation
                latest = package.created_at

            now = datetime.utcnow().replace(tzinfo = pytz.utc)
            day = latest

            while day <= now:                
                self.stdout.write(str(day))
                next_day = day + timedelta(days=1)

                builds = Build.objects.filter(
                    project__package__exact = package,
                    fetched_at__gte = day,
                    fetched_at__lt = next_day)

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
                        created_at = now,
                        successful = successful,
                        failed = failed,
                        errors = errors)

                    stats.save()

                day = next_day
