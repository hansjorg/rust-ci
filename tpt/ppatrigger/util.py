import datetime
from ppatrigger.models import Project
from travis_client import get_last_build_on_branch
from travis_client import restart_build

def trigger_project_build(project):

    build = get_last_build_on_branch(project.username, project.repository, project.branch)
   
    if build:
        last_build_id = build['branch']['id']
        response = restart_build(project.auth_token, last_build_id)

        started = False
        if response and 'result' in response:
            started = response['result'] == True

        if started: 
            project.build_started = True
            project.build_id = last_build_id
            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            project.last_triggered = now
            project.save()

            print('Build successfully started: ' 
                    + str(project))
        else:
            if response:
                if 'flash' in response and 'notice' \
                        in response['flash']:
                    msg = 'Unable to start build of {}, notice: ' +\
                        '"{}"'.format(str(project), response['flash']['notice'])
                else:
                    msg = 'Unable to start build of {} for ' +\
                            'unknown reasons'.format(str(project))
                
                print(msg)
    else:
        # No build returned from Travis, could be that no first
        # build has ever been trigged.
        print('No data returned for project: ' 
                + str(project))


