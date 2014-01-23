from ppatrigger.models import Project
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from util import varnishutil

class Command(BaseCommand):
    args = ''
    help = 'Purge/ban all pages from Varnish except docs'

    def handle(self, *args, **options):

        varnishutil.purge_urls([
            reverse('index'),
            reverse('projects'),
            reverse('help')])

        # Ban all project pages
        varnishutil.ban_cache_groups(Project)

