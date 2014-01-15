from django.db import models
from django.db.models.signals import post_init
from datetime import datetime
from django.utils.timezone import utc
import uuid

class Ppa(models.Model):

    username = models.CharField(max_length=40)
    archive = models.CharField(max_length=40)

    def __unicode__(self):
        return u'%s-%s' % (self.username, self.archive)

class Package(models.Model):

    ppa = models.ForeignKey(Ppa)
    
    name = models.CharField(max_length=40)    
    series = models.CharField(max_length=20)
    arch = models.CharField(max_length=20)

    # Latest version string and creation timestamp
    version = models.CharField(null=True, max_length=100, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    first_created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'%s %s %s' % (self.name, self.series, self.arch)

class ProjectCategory(models.Model):

    name = models.CharField(max_length=100)

    @property
    def project_set_sorted(self):
        return self.project_set.order_by('repository')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Project(models.Model):

    package = models.ForeignKey(Package)
    categories = models.ManyToManyField(ProjectCategory)

    last_build = models.OneToOneField('Build', null=True,
            blank=True, related_name='_unused')
    
    username = models.CharField(max_length=100)
    repository = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)

    deleted = models.BooleanField(default=False, null=False, blank=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Travis token
    auth_token = models.CharField(max_length=100, null=True, blank=True)
    rustci_token = models.CharField(max_length=33, null=False, blank=False)

    created = models.DateTimeField(auto_now_add=True)
    changed = models.DateTimeField(auto_now=True)

    last_triggered = models.DateTimeField(null=True, blank=True)
    build_id = models.CharField(null=True, blank=True, max_length=100)

    build_requested = models.BooleanField(default=True)
    build_started = models.BooleanField(default=False)

    # Retrieved from GitHub via Travis
    author_name = models.CharField(max_length=150, null=True, blank=True)
    author_email = models.CharField(max_length=150, null=True, blank=True)
    # Retrieved from Travis (which gets it from GitHub) 
    description = models.TextField(null=False, blank=True)

    # AWS
    s3_user_name = models.CharField(max_length=100, null=True, blank=True)
    s3_access_key_id = models.CharField(max_length=50, null=True, blank=True)
    s3_secret_access_key = models.CharField(max_length=50, null=True, blank=True) 

    def get_latest_docs(self):
        # Get documentation uploaded for project if any
        docs = None
        try:
            docs = ProjectDocs.objects.filter(project = self).\
                    latest('created_at')
        except ProjectDocs.DoesNotExist:
            pass
        return docs

    def get_project_identifier(self):
        return '{}-{}-{}'.format(self.username, self.repository,
                self.branch)

    def get_absolute_url(self):
        return '/' + self.get_relative_path()

    def get_relative_path(self):
        projects = Project.objects.filter(username = self.username,
                repository = self.repository)

        if(len(projects) > 1):
            # More than one of /username/repository/, use branch too
            url = u'{}/{}/{}'.format(self.username, self.repository,
                    self.branch)
        else:
            # Branch is not master, use it in url
            if(projects[0].branch != 'master'):
                url = u'{}/{}/{}'.format(self.username,
                        self.repository, self.branch)
            else:
                url = '{}/{}'.format(self.username, self.repository)
        return url

    def mark_project_deleted(self):
        self.deleted = True
        self.deleted_at = datetime.utcnow().replace(tzinfo=utc)
        self.save()

    def __unicode__(self):
        if self.deleted:
            desc = u'%s/%s %s (deleted)' % (self.username,
                    self.repository, self.branch)
        else:
            desc = u'%s/%s %s' % (self.username, self.repository,
                    self.branch)
        return desc

    class Meta:
        ordering = ['username', 'repository', 'branch']


def project_post_init(**kwargs):
    project = kwargs.get('instance')
    if(not project.rustci_token):
        project.rustci_token = uuid.uuid4().hex

post_init.connect(project_post_init, Project)


class ProjectDocs(models.Model):
    project = models.ForeignKey(Project)
    created_at = models.DateTimeField(auto_now_add=True)
    build_id = models.IntegerField(null=False)
    build_number = models.IntegerField(null=False)
    job_id = models.IntegerField(null=False)
    # Comma seperated paths: ./doc/{ docpath }/..
    docpaths = models.CharField(max_length=100, null=False)

    def get_docpaths(self):
        paths = None
        if self.docpaths:
            paths = self.docpaths.split(',')
        return paths

class Build(models.Model):

    project = models.ForeignKey(Project)
    package_version = models.CharField(max_length=100)
    package_created_at = models.DateTimeField()

    build_id = models.CharField(max_length=100)

    fetched_at = models.DateTimeField(auto_now_add=True)
    
    result = models.IntegerField()
    # Build status (0 = ok, > 1 = fail,
    # < 0 = error fetching status from Travis)
    status = models.IntegerField()

    duration = models.IntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()

    # Git data for the build

    # Since Travis CI only lets us restart builds with the API, we
    # always try to restart the latest build. This build has Git data
    # from the commit that first triggered it, but since the actual
    # build wasn't triggered by a Git push, this data is not really
    # relevant, but could be interesting for stats.

    committer_email = models.CharField(max_length=150) 
    committer_name = models.CharField(max_length=150) 
    commited_at = models.DateTimeField()
    event_type = models.CharField(max_length=30)    # e.g. 'push'
    commit = models.CharField(max_length=40)        # Git hash
    message = models.TextField()                    # commit message
    compare_url = models.CharField(max_length=150)  # link to diff

    def is_success(self):
        return self.status == 0

    def is_failure(self):
        return self.status > 0

    def __unicode__(self):
        if self.is_success():
            status_text = 'success'
        elif self.is_failure():
            status_text = 'failure'
        else:
            status_text = 'error'
        return u'{} {}'.format(str(self.project), status_text)


    class Meta:
        ordering = ['-started_at', '-fetched_at']

class DailyStats(models.Model):

    package = models.ForeignKey(Package)
    date = models.DateField()
    created_at = models.DateTimeField()
    successful = models.PositiveSmallIntegerField()
    project_count = models.PositiveSmallIntegerField()
    failed = models.PositiveSmallIntegerField()
    errors = models.PositiveSmallIntegerField()
    diff_url = models.CharField(max_length=150)

    class Meta:
        ordering = ['date']
