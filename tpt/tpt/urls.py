from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'ppatrigger.views.index', name='index'),

    url(r'^help/$', 'ppatrigger.views.help', name='help'),

    url(r'^p/add/$', 'ppatrigger.views.add_project', name='add_project'),
    
    # Legacy id based url for redirection
    url(r'^p/(?P<project_id>\d+)/$', 'ppatrigger.views.show_project_by_id', name='project.show_by_id'),
 
    url(r'^p/(?P<project_id>\d+)/trigger$', 'ppatrigger.views.action_trigger_build', name='project.action.trigger_build'),
    url(r'^p/(?P<project_id>\d+)/auth$', 'ppatrigger.views.action_auth_project', name='project.action.get_auth_token'),
  
    # /username/repository/branch
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/(?P<branch>.+?)$', 'ppatrigger.views.show_project', name='project.show'),
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/(?P<branch>.+?)/docs$', 'ppatrigger.views.show_docs', name='project.show_docs'),

    # /username/repository - branch=master
    url(r'^(?P<username>.+?)/(?P<repository>.+?)$', 'ppatrigger.views.show_project', name='project.show'),
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/docs$', 'ppatrigger.views.show_docs', name='project.show_docs'),

    # GitHub callback
    url(r'^callback$', 'ppatrigger.views.github_callback'),

    url(r'^admin/', include(admin.site.urls)),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

