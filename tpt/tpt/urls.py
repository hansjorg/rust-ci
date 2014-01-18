from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'ppatrigger.views.index', name='index'),
    url(r'^projects/$', 'ppatrigger.views.projects_by_category', name='projects'),

    # GitHub callback
    url(r'^callback$', 'ppatrigger.views.github_callback'),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^help/$', 'ppatrigger.views.help', name='help'),
    url(r'^p/add/$', 'ppatrigger.views.add_project', name='add_project'),

    # Putdocs
    url(r'^artifacts/put$', 'ppatrigger.views.put_artifacts_script', name='put_script'),
    url(r'^artifacts/puthook$', 'ppatrigger.views.put_artifacts_hook', name='put_hook'),
    
    # Project actions
    url(r'^p/(?P<project_id>\d+)/$', 'ppatrigger.views.show_project_by_id', name='project.show_by_id'),
    url(r'^p/(?P<project_id>\d+)/artifactconf$', 'ppatrigger.views.action_get_artifact_config', name='project.action.get_artifact_config'),
    url(r'^p/(?P<project_id>\d+)/trigger$', 'ppatrigger.views.action_trigger_build', name='project.action.trigger_build'),
    url(r'^p/(?P<project_id>\d+)/auth$', 'ppatrigger.views.action_auth_project', name='project.action.get_auth_token'),
    url(r'^p/(?P<project_id>\d+)/edit/auth$', 'ppatrigger.views.action_auth_session_then_edit', name='project.action.auth_session_then_edit'),
    url(r'^p/(?P<project_id>\d+)/edit$', 'ppatrigger.views.action_edit_project', name='project.action.edit_project'),
    url(r'^p/(?P<project_id>\d+)/delete$', 'ppatrigger.views.action_delete_project', name='project.action.delete_project'),
    url(r'^p/(?P<project_id>\d+)/delete/confirm$', 'ppatrigger.views.action_delete_project_confirm', name='project.action.delete_project_confirm'),
  
    # /username/repository/branch
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/(?P<branch>.+?)/doc/(?P<docpath>.+?)/(?P<relative_path>.+?)$', 'ppatrigger.views.show_docs', name='project.show_docs'),
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/(?P<branch>.+?)/doc/(?P<docpath>.+?)$', 'ppatrigger.views.show_docs', name='project.show_docs_index'),

    # /username/repository - branch=master
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/doc/(?P<docpath>.+?)/(?P<relative_path>.+?)$', 'ppatrigger.views.show_docs', name='project.show_docs'),
    url(r'^(?P<username>.+?)/(?P<repository>.+?)/doc/(?P<docpath>.+?)$', 'ppatrigger.views.show_docs', name='project.show_docs_index'),

    url(r'^(?P<username>.+?)/(?P<repository>.+?)/(?P<branch>.+?)$', 'ppatrigger.views.show_project', name='project.show'),
    url(r'^(?P<username>.+?)/(?P<repository>.+?)$', 'ppatrigger.views.show_project', name='project.show'),

) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

