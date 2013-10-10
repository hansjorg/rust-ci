from launchpadlib.launchpad import Launchpad

def get_packages(client, instance, username, ppa_name):
    launchpad = Launchpad.login_anonymously(client, instance,
        '/tmp/launchpadlib/')
    ppa = launchpad.people[username].getPPAByName(name=ppa_name)
    return ppa.getPublishedBinaries().entries

def get_package(packages, package_name, series, arch):
    p = None
    arch_series = 'https://api.launchpad.net/1.0/ubuntu/%s/%s' % \
        (series, arch,)

    for package in packages:
        if(package['binary_package_name'] == package_name and
            package['distro_arch_series_link'] == arch_series and
            package['date_superseded'] == None):

            p = package
            break
            
    return p

if __name__ == "__main__":
    packages = get_packages('rust-ci-server', 'production', 'hansjorg', 'rust')
    # Travis CI environment is Ubuntu 12.04 (Precise Pangolin) 64bit
    print get_package_creation_time(packages, 'rust-nightly', 'precise', 'amd64')

