import traceback
import logging
import pytz
from django.core.management.base import BaseCommand
from datetime import datetime
from ppatrigger.models import Project
from tpt import private_settings 

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = ''
    help = 'Delete S3 credentials after given expiration time'

    def handle(self, *args, **options):

        for project in Project.objects.all():
            if project.s3_creds_created_at:
                now = datetime.utcnow().replace(tzinfo = pytz.utc)
                diff = now - project.s3_creds_created_at

                    if diff.seconds > private_settings.CREDENTIALS_MAX_AGE:
                        if not project.build_started and not project.build_requested:
                            logger.info('Credentials older than max age, deleting: %s',
                                    project)

                            project.delete_s3_credentials()
                            project.save()
                        else:
                            logger.info('Credentials older than max age, but build ' +\
                                    'was requested or started so not deleting: %s', project)


