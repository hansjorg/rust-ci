import urllib2
import json

TRAVIS_BASE = 'https://api.travis-ci.org'

def call(url, token = None, data = None):
    json_data = None
    if data:
        json_data = json.dumps(data)

    request = urllib2.Request(TRAVIS_BASE + url, json_data)

    if token:
        request.add_header('Authorization', 'token ' + token)
    request.add_header('Content-Type',
            'application/json; charset=UTF-8')

    try:    
        response = urllib2.urlopen(request)
    except urllib2.HTTPError, error:
        print('Travis Client got error response: ' + str(error.code))
        print(error.read())

        return None
 
    response_data = response.read()

    result = None
    if response_data:
        try:
            result = json.loads(response_data)
        except ValueError:
            print 'Unable to deserialize json. Response: "{}"'.\
                    format(response_data)

    return result

def restart_build(travis_token, build_id):
    return call('/requests', travis_token, { 'build_id': build_id })

def get_repo_builds(owner_name, repo_name):
    return call('/repos/{}/{}/builds'.format(owner_name, repo_name))

def get_last_build_on_branch(owner_name, repo_name, branch):
    return call('/repos/{}/{}/branches/{}'.format(owner_name, repo_name, branch))

def get_build_by_id(id):
    return call('/builds/{}'.format(id))

def get_log(log_id):
    return call('/logs/{}'.format(log_id))

def get_uptime():
    return call('/uptime/')

# Helper functions

def trigger_branch_build_restart(travis_token, owner_name, repo_name, branch):
    last_build_id = get_last_build_on_branch(owner_name, repo_name, branch)['branch']['id']
    return restart_build(travis_token, last_build_id)

def trigger_build_restart(travis_token, owner_name, repo_name):
    last_build_id = get_repo_builds(owner_name, repo_name)[0]['id']
    return restart_build(travis_token, last_build_id)['result']

if __name__ == "__main__":
    owner_name = 'hansjorg'
    repo_name = 'rust-protobuf'
    branch = 'rust-0.8'
    
    #result = trigger_branch_build_restart(test_token, owner_name, repo_name, branch)
    #print(json.dumps(result, sort_keys=True, indent=4))
    
    #result = get_last_build_on_branch(owner_name, repo_name, branch)

    result = get_build_by_id('12208592')
    print(json.dumps(result, sort_keys=True, indent=4))

    #result = get_repo_builds(owner_name, repo_name)
    #result = trigger_build_restart(test_token, owner_name, repo_name)


