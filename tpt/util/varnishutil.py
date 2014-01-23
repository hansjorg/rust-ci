import inspect
from tpt import private_settings
from varnish import VarnishManager, http_purge_url

varnish = private_settings.VARNISH_MANAGEMENT_HOST + ':' +\
        str(private_settings.VARNISH_MANAGEMENT_PORT)
manager = VarnishManager((varnish,))

def purge_urls(urls):

    if not type(urls) is list:
        urls = [urls]

    for path in urls:
        url = 'http://{}:{}{}'.format(private_settings.VARNISH_HOST,
                private_settings.VARNISH_PORT, path)
        http_purge_url(url)


def ban_cache_groups(cache_groups):
 
    if not type(cache_groups) is list:
        cache_groups = [cache_groups]

    for obj in cache_groups:
        if type(obj) is str:
            group = obj
        elif inspect.isclass(obj):
            group = obj.class_cache_group

        ban_expr = 'obj.http.x-cache-group ~ "{}"'.format(group)

        manager.run('ban', ban_expr,
                secret=private_settings.VARNISH_SECRET)

    #print(manager.run('ban.list',
    #    secret=private_settings.VARNISH_SECRET))
    

def set_cache_group(response, obj):

    if type(obj) is str:
        response['X-Cache-Group'] = obj
    else: 
        response['X-Cache-Group'] = obj.get_cache_groups()

