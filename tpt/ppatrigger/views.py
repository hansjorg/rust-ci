import random
import json
import urllib2
from urllib import urlencode
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from django.core.mail import mail_admins
from django.conf import settings
from tpt import private_settings
from models import Project, Build
from forms import ProjectForm

def index(request, error_message = None):
    projects = Project.objects.all()

    context = {
            'title': private_settings.APP_TITLE,
            'projects': projects,
            'error_message': error_message,
    }
    return render(request, 'ppatrigger/index.html', context)

def help(request):
    context = {
            'title': private_settings.APP_TITLE,
    }
    return render(request, 'ppatrigger/help.html', context)


def add_project(request):

    if request.method == 'POST':
        form = ProjectForm(request.POST)

        if form.is_valid():

            package = form.cleaned_data['package']
            username = form.cleaned_data['username']
            repository = form.cleaned_data['repository']
            branch = form.cleaned_data['branch']

            project = Project(package = package, username = username,
                    repository = repository, branch = branch)
            project.save()

            state = '{:x}'.format(random.randrange(16**30))
            request.session['state'] = state
            request.session['project_id'] = project.id

            redirect_uri = private_settings.GITHUB_REDIRECT_URI
            return HttpResponseRedirect('https://github.com/login/'
                    'oauth/authorize?client_id={}&scope=public_repo'
                    '&state={}&redirect_uri={}'.format(
                        private_settings.GITHUB_CLIENT_ID, state,
                        urllib2.quote(redirect_uri))
                    )
    else:
        form = ProjectForm(initial={'branch': 'master'})

    context = {
            'title': private_settings.APP_TITLE,
            'form': form
    }
    return render(request, 'ppatrigger/add_project.html', context)


def show_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    builds = Build.objects.filter(project_id__exact = project_id)

    return render(request, 'ppatrigger/show_project.html',
            {'project': project,
            'builds': builds,
            'title': private_settings.APP_TITLE})

def github_callback(request):
    state = request.session['state'] if 'state' in request.session else None
    if not state or request.GET['state'] != state:
        return HttpResponse('Unauthorized', status=401)

    data = {
        'client_id': private_settings.GITHUB_CLIENT_ID,
        'client_secret': private_settings.GITHUB_CLIENT_SECRET,
        'code': request.GET['code'],
        'state': request.GET['state']
    }
    req = urllib2.Request('https://github.com/login/oauth/access_token',
            urlencode(data))
    req.add_header('Accept', 'application/json')
    response = json.loads(urllib2.urlopen(req).read())

    project_id = request.session['project_id']
    project = Project.objects.get(pk = project_id)

    if 'access_token' in response and response['access_token']:
        data = { 'github_token': response['access_token'] }
        req = urllib2.Request('https://api.travis-ci.org/auth/github',
                urlencode(data))
        req.add_header('Accept', 'application/json')
        travis_response = json.loads(urllib2.urlopen(req).read())

        if 'access_token' in travis_response and \
                travis_response['access_token']:
            project.auth_token = travis_response['access_token']
            project.save()

            if not settings.DEBUG:
                mail_message = "{}/{} - {}\n\n".\
                        format(project.username, project.repository,
                                project.branch)
                mail_admins('Project added', mail_message)

            return HttpResponseRedirect(reverse('ppatrigger.views.index'))

        else:
            error_message = 'Error in response from Travis'

    else:
        error_message = 'Error in response from GitHub: {}'.\
                format(response.get('error'))

    project.delete()

    return index(request, error_message)

