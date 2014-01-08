from django.db import models

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


class Project(models.Model):

    package = models.ForeignKey(Package)
    last_build = models.OneToOneField('Build', null=True,
            related_name='_unused')
    
    username = models.CharField(max_length=100)
    repository = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)

    deleted = models.BooleanField(default=False, null=False, blank=False)

    # Travis token
    auth_token = models.CharField(max_length=100,null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    changed = models.DateTimeField(auto_now=True)

    last_triggered = models.DateTimeField(null=True, blank=True)
    build_id = models.CharField(null=True, max_length=100)

    build_requested = models.BooleanField(default=True)
    build_started = models.BooleanField(default=False)

    # Retrieved from GitHub via Travis
    author_name = models.CharField(max_length=150, null=True)
    author_email = models.CharField(max_length=150, null=True)

    def __unicode__(self):
        return u'%s/%s %s' % (self.username, self.repository,
                self.branch)

    class Meta:
        unique_together = (('username', 'repository', 'branch'),)
        ordering = ['username', 'repository', 'branch']

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
