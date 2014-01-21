import requests
from django.http import HttpResponseRedirect, HttpResponse, Http404

def proxy_request(request, url):

    headers = request.META
    params = request.GET.copy()

    args = {}

    #args['headers'] = headers
    #args['params'] = params

    response = requests.request(request.method, url, **args)

    proxy_response = HttpResponse(response.content,
            status=response.status_code)

    content_type = response.headers['content-type']
    proxy_response['Content-Type'] =  content_type

    return proxy_response
