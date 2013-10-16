import traceback
from dateutil import parser
from django.db import connection
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from ppatrigger.models import Project
from ppatrigger.models import Build
from travis_client import get_build_by_id
import json

class Command(BaseCommand):
    args = ''
    help = 'Fetch data for builds that have been marked as started'

    def handle(self, *args, **options):


        projects = Project.objects.filter(build_started__exact = True)

        if not len(projects):
            self.stdout.write('fetchbuilds: No started builds.')
        else:

            self.stdout.write('fetchbuilds: Fetching data for {} '
                    'started builds.'.format(len(projects)))

            for project in projects:

                # A run of the checkpackage command has triggered a
                # build which may have finished by now. Check and
                # save a build data entry if so.

                build = get_build_by_id(project.build_id)

                if build and 'state' in build:
                    build_state = build['state']

                    if build_state == 'finished':
                        self.stdout.write(str(project) + ': Build '
                                'finished, saving data ')

                        # Result and status for some builds have been returned
                        # as null from Travis for some reason
                        result = -1
                        if build['result']:
                            result = build['result']

                        status = -1
                        if build['status']:
                            status = build['status']

                        build_data = Build(
                                project = project,
                                build_id = build['id'],
                                package_version = project.package.version,
                                package_created_at = project.package.created_at,
                                result = result,
                                status = status,
                                duration = build['duration'],
                                started_at = parser.parse(build['started_at']),
                                finished_at = parser.parse(build['finished_at']),
                                committer_email = build['committer_email'],
                                committer_name = build['committer_name'],
                                commited_at = parser.parse(build['committed_at']),
                                event_type = build['event_type'],
                                commit = build['commit'],
                                message = build['message'],
                                compare_url = build['compare_url']
                        )
                        try:
                            build_data.save()

                            project.last_build = build_data
                            project.build_started = False
                            project.author_name = build['author_name']
                            project.author_email = build['author_email']
                            project.save()
                        except IntegrityError:
                            # TODO: temp fix for missing result from Travis
                            connection._rollback()
                            self.stdout.write(str(project) + ': Error storing build state for project')
                            self.stdout.write(json.dumps(build, sort_keys=True, indent=4))

                            self.stdout.write(traceback.format_exc())

                    else:
                        self.stdout.write(str(project) + ': Build not '
                                'finished, state: ' + build_state)


    
