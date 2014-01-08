import re
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
from models import Project, Build, DailyStats
from forms import ProjectForm
from travisclient import get_travis_token

def index(request, error_message = None):
    projects = Project.objects.filter(deleted = False)
    dailystats = DailyStats.objects.all()

    today = None
    yesterday = None
    successful_diff = None
    failed_diff = None
    try:
        today = dailystats[len(dailystats) - 1]
        yesterday = dailystats[len(dailystats) - 2]

        successful_diff = today.successful - yesterday.successful
        if successful_diff > 1:
            successful_diff = '+' + str(successful_diff)
        failed_diff = today.failed - yesterday.failed
        if failed_diff > 1:
            failed_diff = '+' + str(failed_diff)
    except:
        pass

    context = {
            'title': private_settings.APP_TITLE,
            'projects': projects,
            'dailystats': dailystats,
            'today': today,
            'successful_diff': successful_diff,
            'failed_diff': failed_diff, 
            'error_message': error_message,
    }
    return render(request, 'ppatrigger/index.html', context)

def help(request):
    context = {
            'title': private_settings.APP_TITLE,
    }
    return render(request, 'ppatrigger/help.html', context)

def show_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    builds = Build.objects.filter(project_id__exact = project_id)

    # Iterate over builds and create GitHub hash compare
    # fragments like 'cd59a7c...886a4dd' for linking to diff
    if len(builds):
        prev_build = builds[len(builds) - 1]
        # extract Git hash from version strings like:
        # 201310190805~34a1e3d~precise
        version_pattern = re.compile('.*~(.*)~.*')
        for build in reversed(builds):
            match = version_pattern.match(build.package_version)
            if match:
                build.git_hash = match.group(1)

            if prev_build.package_version != build.package_version:
                build.git_diff = prev_build.git_hash + '...' + build.git_hash

            prev_build = build

    return render(request, 'ppatrigger/show_project.html',
            {'project': project,
            'builds': builds,
            'title': private_settings.APP_TITLE})


def trigger_build(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    return authenticate_with_github(request, project.id,
            'trigger_rebuild')

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

            return authenticate_with_github(request, project.id,
                    'add_project')

    else:
        form = ProjectForm(initial={'branch': 'master'})

    context = {
            'title': private_settings.APP_TITLE,
            'form': form
    }
    return render(request, 'ppatrigger/add_project.html', context)


def authenticate_with_github(request, project_id, auth_reason):
    project = Project.objects.get(pk = project_id)

    state = '{:x}'.format(random.randrange(16**30))
    request.session['state'] = state
    request.session['project_id'] = project.id
    request.session['auth_reason'] = auth_reason

    redirect_uri = private_settings.GITHUB_REDIRECT_URI
    return HttpResponseRedirect('https://github.com/login/'
            'oauth/authorize?client_id={}&scope=public_repo'
            '&state={}&redirect_uri={}'.format(
                private_settings.GITHUB_CLIENT_ID, state,
                urllib2.quote(redirect_uri))
            )


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
        github_token = response['access_token']

        req = urllib2.Request('https://api.github.com/user')
        req.add_header('Accept', 'application/json')
        req.add_header('Authorization', 'token {}'.
                format(github_token))
        github_user = json.loads(urllib2.urlopen(req).read())

        auth_reason = request.session['auth_reason']
       
        #print(json.dumps(github_user, sort_keys=True, indent=4))

        # Get organizations for user (to allow members of orgs to 
        # add projects on behalf of their organization)
        orgs_req = urllib2.Request(github_user['organizations_url'])
        orgs_req.add_header('Accept', 'application/json')
        orgs_req.add_header('Authorization', 'token {}'.
                format(github_token))
        github_user_orgs = json.loads(urllib2.urlopen(orgs_req).read())

        #print(json.dumps(github_user_orgs, sort_keys=True, indent=4))

        is_authorized = False
        # Check that we got token for the right user or organization
        if project.username == github_user['login']:
            is_authorized = True
        else:
            for github_org in github_user_orgs:
                if project.username == github_org['login']:
                    is_authorized = True
                    break

        if not is_authorized:
            if auth_reason == 'add_project':
                project.delete()
            return HttpResponse('Wrong username (does not match logged\
                    in user or users organizations)', status=401)
        
        if auth_reason == 'delete_project':
            if not settings.DEBUG:
                mail_message = "{}/{} - {}\n\n".\
                        format(project.username, project.repository,
                                project.branch)
                mail_admins('Project deleted', mail_message)
            
            project.delete()
            return HttpResponseRedirect(reverse('ppatrigger.views.index'))

        else:
            travis_token = get_travis_token(github_token)

            if travis_token:
                if auth_reason == 'add_project':
                    project.auth_token = travis_token
                    project.save()
                    
                    if not settings.DEBUG:
                        mail_message = "{}/{} - {}\n\n".\
                                format(project.username, project.repository,
                                        project.branch)
                        mail_admins('Project added', mail_message)

                elif auth_reason == 'trigger_rebuild':
                    project.build_requested = True 
                    project.save()
            
                return HttpResponseRedirect(reverse('ppatrigger.views.index'))
            else:
                error_message = 'Error in response from Travis'

    else:
        error_message = 'Error in response from GitHub: {}'.\
                format(response.get('error'))

    project.delete()

    return index(request, error_message)

