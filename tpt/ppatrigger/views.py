import re
import random
import json
import urllib2
import travisclient
from urllib import urlencode
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_protect
from django.core.urlresolvers import reverse
from django.core.mail import mail_admins
from django.conf import settings
from django.core import serializers
from tpt import private_settings
from util import iamutil, proxyutil
from models import Project, ProjectCategory, ProjectDocs, Build, DailyStats
from forms import ProjectForm, ProjectFormEdit
import logging

logger = logging.getLogger(__name__)

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

def projects_by_category(request):
    uncategorized = Project.objects.filter(categories=None,
            deleted=False).\
            order_by('repository')

    context = {
            'title': private_settings.APP_TITLE,
            'categories': ProjectCategory.objects.all(),
            'uncategorized': uncategorized,
    }
    return render(request, 'ppatrigger/projects_by_category.html',
            context)


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
        error_message = None, rustci_secure_token = None,
        delete_project = False):
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

    return render(request, 'ppatrigger/show_project.html',
            {'project': project,
            'builds': builds,
            'error_message': error_message,
            'rustci_secure_token': rustci_secure_token,
            'title': private_settings.APP_TITLE,
            'delete_project': delete_project})


# Show documentation artifacts for project
def show_docs(request, username, repository, docpath, relative_path = None,
        branch = 'master'):
    try:
        project = Project.objects.get(username = username,
                repository = repository,
                branch = branch, deleted = False)
    except Project.DoesNotExist:
        raise Http404

    project_docs = ProjectDocs.objects.filter(project = project).\
            latest('created_at')

    if docpath.endswith('/'):
        docpath = docpath[:-1]

    proxy_url = private_settings.DOCS_URL_BASE +\
        project.get_project_identifier() + '/' +\
        str(project_docs.build_id) + '/' + str(project_docs.job_id) +\
        '/' + docpath + '/'

    if relative_path:
        proxy_url += relative_path
    else:
        proxy_url += 'index.html'

    return proxyutil.proxy_request(request, proxy_url)


def action_auth_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    return authenticate_with_github(request, project.id,
            'get_auth_token')

@csrf_protect
def action_delete_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    return show_project(request, project.username, project.repository,
            project.branch, delete_project = True)

@csrf_protect
def action_delete_project_confirm(request, project_id):
    if not request.method == 'POST':
        return HttpResponse('Method not allowed', status=405)

    project = get_object_or_404(Project, pk=project_id)

    return authenticate_with_github(request, project.id,
            'delete_project')

# 1) This is called
# 2) User is redirected to GitHub for auth
# 3) Local auth token is set in session
# 4) User is redirected to edit form where token is checked
def action_auth_session_then_edit(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    return authenticate_with_github(request, project.id,
            'edit_project')


@csrf_protect
def action_edit_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    auth_token = request.session.get('session_auth')
    if not auth_token == project.rustci_token:
        logger.error('Unauthorized edit attempt. auth_token={}'.\
                format(auth_token))
        return HttpResponse('Unauthorized (not allowed to edit)',
                status=401)

    if request.method == 'POST':
        form = ProjectFormEdit(request.POST)

        if form.is_valid():
            project.package = form.cleaned_data['package']
            project.branch = form.cleaned_data['branch']
            project.categories = form.cleaned_data['categories']
            project.save()           
            
            return HttpResponseRedirect(reverse(
                'project.show_by_id',
                args=(project.id,)))

    else:
        form = ProjectFormEdit(initial={
            'username': project.username,
            'repository': project.repository,
            'branch': project.branch,
            'categories': project.categories.all()})

    context = {
            'title': private_settings.APP_TITLE,
            'project': project,
            'form': form,
            'editing': True,
            'categories': ProjectCategory.objects.all()
    }
    return render(request, 'ppatrigger/project_form.html', context)


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


@csrf_protect
def add_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)

        if form.is_valid():
            package = form.cleaned_data['package']
            username = form.cleaned_data['username']
            repository = form.cleaned_data['repository']
            branch = form.cleaned_data['branch']
            categories = form.cleaned_data['categories']

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

            # Set categories
            project.categories = categories
            project.save()

            return authenticate_with_github(request, project.id,
                    'add_project')

    else:
        form = ProjectForm(initial={'branch': 'master'})

    context = {
            'title': private_settings.APP_TITLE,
            'form': form,
            'categories': ProjectCategory.objects.all()
    }
    return render(request, 'ppatrigger/project_form.html', context)


def put_artifacts_script(request):

    token = request.GET.get('t', None)    
  
    try:
        project = Project.objects.get(rustci_token = token,
                deleted = False)
    except Project.DoesNotExist:
        logger.error('Project not found when requesting put_artifacts ' +
            'script. token={}'.format(token))
        return HttpResponse('Unauthorized', status=401)

    if not project.s3_user_name:
        user = iamutil.create_iam_user(project.get_project_identifier())

        project.s3_user_name = user['user_name']
        project.s3_access_key_id = user['access_key_id']
        project.s3_secret_access_key = user['secret_access_key']

        project.save()

    key_id = project.s3_access_key_id.encode('utf-8')
    key = project.s3_secret_access_key.encode('utf-8')

    context = {
            'project_identifier': project.get_project_identifier(),
            's3_access_key_id': key_id,
            's3_secret_access_key': key,
            'rustci_token': project.rustci_token
    }
    return render(request, 'ppatrigger/put_artifacts_script.txt', context,
            content_type='text/plain')


def put_artifacts_hook(request):
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
        logger.error('Project not found when requesting put_artifacs ' +
            'hook. token={}, build_id={}'.format(token, build_id))
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
    state = request.session.get('state')
    state_param = request.GET['state']
    if not state or state_param != state:
        logger.error('github_callback failed, no state given or ' +
            'not matching. session={}, param={}'.format(state, state_param))
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
                # Unable to authorize when adding, delete
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
            
            project.mark_project_deleted()
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
            
                elif auth_reason == 'edit_project':
                    request.session['session_auth'] = project.rustci_token
       
                    return HttpResponseRedirect(reverse(
                        'project.action.edit_project',
                        args=(project.id,)))

                return HttpResponseRedirect(reverse('ppatrigger.views.index'))
            else:
                error_message = 'Error in response from Travis CI'

    else:
        if auth_reason == 'add_project':
            # Unable to authorize when adding, delete
            project.delete()

        error_message = 'Error in response from GitHub: {}'.\
                format(response.get('error'))

    return index(request, error_message)

