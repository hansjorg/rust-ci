from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from ppatrigger.models import Project, ProjectDocs, DailyStats
from util import varnishutil
import views

@receiver(post_save, sender=Project)
def project_handler(sender, instance, **kwargs):
    # Purge front page, projects page and project details from varnish
    varnishutil.purge_urls([
        reverse('index'),
        reverse('projects'),
        instance.get_absolute_url()])


@receiver(post_save, sender=ProjectDocs)
def project_docs_handler(sender, instance, **kwargs):
    # Ban all project docs from varnish
    varnishutil.ban_cache_groups(instance.get_cache_groups())


@receiver(post_save, sender=DailyStats)
def daily_stats_handler(sender, instance, **kwargs):
    # Purge front page
    varnishutil.purge_urls(reverse('index'))

