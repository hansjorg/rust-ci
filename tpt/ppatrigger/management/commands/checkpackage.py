import datetime
import pytz
from dateutil import parser
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from util.ppautil import get_packages, get_package
from ppatrigger.models import Package, Project
from tpt import private_settings
from travisclient import get_last_build_on_branch
from travisclient import restart_build, AuthException

class Command(BaseCommand):
    args = '<package_id package_id ...>'
    help = 'Check if the given package(es) have been updated'

    def handle(self, *args, **options):
        if len(args) == 0:
            raise CommandError('Provide at least one package id '
                'on the format name.ubunutuseries.arch')

        for packageid in args:

            try:
                p = packageid.split('.')

                package = Package.objects.get(name__exact = p[0],
                    series__exact = p[1], arch__exact = p[2])

                self.stdout.write('Checking status of "%s"' % package)
            except IndexError:
                raise CommandError('Package id "%s" not on format '
                    'name.ubuntuseries.arch' % packageid)
            except Package.DoesNotExist:
                raise CommandError('Package with id "%s" does not '
                    'exist' % packageid)

            ppa = package.ppa

            packages = get_packages(
                    private_settings.LAUNCHPAD_CLIENT_NAME,
                    private_settings.LAUNCHPAD_INSTANCE,
                    ppa.username,
                    ppa.archive)

            package_data = get_package(packages,
                package.name,
                package.series,
                package.arch)

            creation_time_str = package_data['date_created']
            creation_time = parser.parse(creation_time_str)
            version = package_data['binary_package_version']

            package.created_at = creation_time
            package.version = version
            package.save()

            self.stdout.write('Creation time "%s"' % creation_time_str)

            self.check_package(package, creation_time)

    def check_package(self, package, timestamp):
        projects = Project.objects.filter(
            Q(package = package, deleted = False),
            Q(build_requested__exact = True) |
                    Q(last_triggered__lt = timestamp))

        for project in projects:
            if project.auth_token and not project.build_started:
                self.stdout.write('Going to trigger build for '
                        'project: ' + str(project))

                self.trigger_project_build(project, timestamp)
            elif project.build_started:
                self.stdout.write('Skipping project with build '
                    'in progress: ' + str(project))
            else:
                self.stdout.write('Skipping project due to missing ' 
                        'auth token: ' + str(project))

    def trigger_project_build(self, project, timestamp):

        build = get_last_build_on_branch(project.username, project.repository, project.branch)

        if build:
            last_build_id = build['branch']['id']

            response = None
            try:
                response = restart_build(project.auth_token, last_build_id)
            except AuthException:
                self.scratch_auth_token(project)

            started = False
            if response and 'result' in response:
                started = response['result'] == True

            if started:
                project.build_started = True
                project.build_requested = False
                project.build_id = last_build_id
                now = datetime.datetime.utcnow().replace(tzinfo =
                        pytz.utc)
                project.last_triggered = now
                project.save()

                self.stdout.write('Build successfully started: ' 
                        + str(project))
            else:
                if response:
                    if 'flash' in response and 'notice' \
                            in response['flash']:
                        msg = 'Unable to start build of {}, notice: ' +\
                            '"{}"'.format(str(project), response['flash']['notice'])
                    else:
                        msg = 'Unable to start build of {} for ' +\
                                'unknown reasons'.format(str(project))
                    
                    self.stdout.write(msg)
        else:
            # No build returned from Travis, could be that no first
            # build has ever been trigged.
            self.stdout.write('No data returned for project: ' 
                    + str(project))


    def scratch_auth_token(self, project):
        self.stdout.write('Got auth error from Travis, scratching token for project: ' 
                    + str(project))
        project.auth_token = None
        project.save()
 
