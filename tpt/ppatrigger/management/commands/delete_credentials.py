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

                logger.info('Credentials older than max age, deleting: %s',
                        project)

                if diff.seconds > private_settings.CREDENTIALS_MAX_AGE:
                    project.delete_s3_credentials()
                    project.save()

