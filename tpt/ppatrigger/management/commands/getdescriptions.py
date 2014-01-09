import traceback
from django.core.management.base import BaseCommand
from ppatrigger.models import Project
from travisclient import get_repo

# For getting project description field from Travis CI
# New projects get when added, this command is to update existing
class Command(BaseCommand):
    args = ''
    help = 'Fetch/update project descriptions for all projects'

    def handle(self, *args, **options):

        for project in Project.objects.filter(deleted = False):

            repo = get_repo(project.username, project.repository)

            if(repo and 'description' in repo and
                    repo['description']):
                project.description = repo['description']
                project.save()
            
                self.stdout.write(str(project) + ': ' +\
                        project.description)
            else:
                self.stdout.write('No description found: ' + str(project))

