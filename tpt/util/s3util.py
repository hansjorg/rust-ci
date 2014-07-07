import boto
import logging
from tpt import private_settings
from boto.s3.key import Key
from django.http import StreamingHttpResponse
from django.http import Http404

logger = logging.getLogger(__name__)

def stream_object(key_name):

    s3 = boto.connect_s3(
            aws_access_key_id = private_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = private_settings.AWS_SECRET_ACCESS_KEY)

    bucket = s3.get_bucket(private_settings.AWS_S3_BUCKET, validate=False)

    key = bucket.get_key(key_name)

    if not key:
        logger.warn('Unable to find key "{}" in bucket "{}"'.format(key_name,
            private_settings.AWS_S3_BUCKET))
        raise Http404()

    response = StreamingHttpResponse(key)

    if key.etag:
        response['Etag'] = key.etag

    if key.content_type:
        response['Content-Type'] =  key.content_type
    else:
        response['Content-Type'] = 'text/plain'
    
    if key.size:
        response['Content-Length'] =  key.size
    
    return response

