from ppatrigger.models import Project
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from util import varnishutil

class Command(BaseCommand):
    args = '<cache_group cache_group ...>'
    help = 'Purge/ban all pages from Varnish except docs, ' +\
            'or given cache group(s)'

    def handle(self, *args, **options):

        if len(args) == 0:
            varnishutil.purge_urls([
                reverse('index'),
                reverse('projects'),
                reverse('help')])

            # Ban all project pages
            varnishutil.ban_cache_groups(Project)
        else:
            # Ban all given cache groups

            varnishutil.ban_cache_groups(list(args))

