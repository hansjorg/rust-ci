import re
import random
import json
import urllib2
import travisclient
from urllib import urlencode
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import mail_admins
from django.conf import settings
from tpt import private_settings
from util import iamutil
from models import Project, ProjectDocs, Build, DailyStats
from forms import ProjectForm

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


# Redirect old project url's using id
def show_project_by_id(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return redirect(project)

def show_project(request, username, repository, branch = 'master',
        error_message = None, rustci_secure_token = None):
    try:
        project = Project.objects.get(username = username,
                repository = repository,
                branch = branch, deleted = False)
    except Project.DoesNotExist:
        raise Http404 
    builds = Build.objects.filter(project_id__exact = project.id)

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


    # Get documentation if any
    docs = None
    try:
        docs = ProjectDocs.objects.filter(project = project).\
                latest('created_at')
    except ProjectDocs.DoesNotExist:
        pass

    return render(request, 'ppatrigger/show_project.html',
            {'project': project,
            'builds': builds,
            'error_message': error_message,
            'rustci_secure_token': rustci_secure_token,
            'title': private_settings.APP_TITLE,
            'docpaths': docs.get_docpaths() if docs else None})


# Show documentation artifacts for project
def show_docs(request, username, repository, docpath, relative_path = None, branch = 'master'):
    try:
        project = Project.objects.get(username = username,
                repository = repository,
                branch = branch, deleted = False)
    except Project.DoesNotExist:
        raise Http404

    project_docs = ProjectDocs.objects.filter(project = project).\
            latest('created_at')

    return render(request, 'ppatrigger/show_docs.html', 
        {'project_docs': project_docs, 
        'docpath': docpath,
        'relative_path': relative_path,
        'title': private_settings.APP_TITLE})


def action_auth_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    return authenticate_with_github(request, project.id,
            'get_auth_token')


def action_trigger_build(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    return authenticate_with_github(request, project.id,
            'trigger_rebuild')

def action_get_artifact_config(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    token = project.rustci_token.encode('utf-8')

    rustci_secure_token = travisclient.get_secure_env_var(
            project.username, project.repository, 'RUSTCI_TOKEN',
            token)

    return show_project(request, project.username, project.repository,
            project.branch, rustci_secure_token = rustci_secure_token)


def add_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)

        if form.is_valid():
            package = form.cleaned_data['package']
            username = form.cleaned_data['username']
            repository = form.cleaned_data['repository']
            branch = form.cleaned_data['branch']

            repo = travisclient.get_repo(username, repository)

            if not repo:
                error_message = 'Unable to get Travis CI repo: {}/{}'.\
                    format(username, repository)
                return index(request, error_message)

            project = Project(package = package, username = username,
                    repository = repository, branch = branch)
           
            if('description' in repo):
                project.description = repo['description']
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


def putdocs_script(request):

    token = request.GET.get('t', None)    
  
    try:
        project = Project.objects.get(rustci_token = token,
                deleted = False)
    except Project.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)

    if not project.s3_user_name:
        user = iamutil.create_iam_user(project.get_project_identifier())

        project.s3_user_name = user['user_name']
        project.s3_access_key_id = user['access_key_id']
        project.s3_secret_access_key = user['secret_access_key']

        project.save()

    # Encrypt with project's public key
    #key_id = travisclient.get_secure_string(project.username,
    #        project.repository,
    #        project.s3_access_key_id.encode('utf-8'))
    #key = travisclient.get_secure_string(project.username,
    #        project.repository,
    #        project.s3_secret_access_key.encode('utf-8'))

    key_id = project.s3_access_key_id.encode('utf-8')
    key = project.s3_secret_access_key.encode('utf-8')

    context = {
            's3_access_key_id': key_id,
            's3_secret_access_key': key
    }
    return render(request, 'ppatrigger/putdocs_script.txt', context,
            content_type='text/plain')


def putdocs_hook(request):
    token = request.GET.get('token', None)    
    build_id = request.GET.get('build', None)    
    job_id = request.GET.get('job', None)
    build_number = request.GET.get('buildnumber', None)
    docpaths = request.GET.get('docpaths', None)    

    try:
        project = Project.objects.get(rustci_token = token,
                deleted = False)
       
        docs = ProjectDocs(project = project, build_id = build_id,
                job_id = job_id, build_number = build_number,
                docpaths = docpaths)
        docs.save()

    except Project.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)

    return HttpResponse('OK', content_type='text/plain',
            status=200)


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

    project_id = request.session['project_id']
    project = Project.objects.get(pk = project_id)

    auth_reason = request.session['auth_reason']

    request.session.clear()

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

    if 'access_token' in response and response['access_token']:
        github_token = response['access_token']

        req = urllib2.Request('https://api.github.com/user')
        req.add_header('Accept', 'application/json')
        req.add_header('Authorization', 'token {}'.
                format(github_token))
        github_user = json.loads(urllib2.urlopen(req).read())
       
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

            error_message = 'Neither authenticated GitHub user ({}) \
                    or that users organizations matches project \
                    owner ({})'.format(github_user['login'],
                    project.username)
            return show_project(request, project.username,
                    project.repository, project.branch,
                    error_message)

        if auth_reason == 'delete_project':
            if not settings.DEBUG:
                mail_message = "{}/{} - {}\n\n".\
                        format(project.username, project.repository,
                                project.branch)
                mail_admins('Project deleted', mail_message)
            
            project.deleted = True
            project.save
            return HttpResponseRedirect(reverse('ppatrigger.views.index'))

        else:
            travis_token = travisclient.get_travis_token(github_token)

            if travis_token:
                if auth_reason == 'add_project':
                    project.auth_token = travis_token
                    project.save()
                    
                    if not settings.DEBUG:
                        mail_message = "{}/{} - {}\n\n".\
                                format(project.username, project.repository,
                                        project.branch)
                        mail_admins('Project added', mail_message)

                elif auth_reason == 'get_auth_token':
                    # Used if initial auth failed for some reason
                    # (i.e. no auth_token in db)
                    project.auth_token = travis_token
                    project.save()

                    if not settings.DEBUG:
                        mail_message = "{}/{} - {}\n\n".\
                                format(project.username, project.repository,
                                        project.branch)
                        mail_admins('Project authenticated', mail_message)

                elif auth_reason == 'trigger_rebuild':
                    project.auth_token = travis_token
                    project.build_requested = True 
                    project.save()                
            
                return HttpResponseRedirect(reverse('ppatrigger.views.index'))
            else:
                error_message = 'Error in response from Travis CI'

    else:
        error_message = 'Error in response from GitHub: {}'.\
                format(response.get('error'))

    project.delete()

    return index(request, error_message)

