from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'tpt.views.home', name='home'),
    # url(r'^tpt/', include('tpt.foo.urls')),
    
    url(r'^$', 'ppatrigger.views.index', name='index'),
    url(r'^help/$', 'ppatrigger.views.help', name='help'),
    url(r'^p/add/$', 'ppatrigger.views.add_project', name='add_project'),
    url(r'^p/(?P<project_id>\d+)/$', 'ppatrigger.views.show_project', name='show_project'),
    
    url(r'^callback$', 'ppatrigger.views.github_callback'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),
)
