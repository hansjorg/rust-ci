import traceback
from django.core.management.base import BaseCommand
from ppatrigger.models import Project
from travisclient import get_repo

# For updating existing projects with new additions
#   * get project description field from Travis CI
#   * set rustci_token (implicit trigger)
class Command(BaseCommand):
    args = ''
    help = 'Fetch/update project descriptions for all projects'

    def handle(self, *args, **options):

        for project in Project.objects.filter(deleted = False):

            repo = get_repo(project.username, project.repository)

            if(repo and 'description' in repo and
                    repo['description']):
                project.description = repo['description']
            
                self.stdout.write(str(project) + ': ' +\
                        project.description)
            else:
                self.stdout.write('No description found: ' + str(project))

            project.save()
