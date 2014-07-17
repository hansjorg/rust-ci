import boto
from boto.exception import BotoServerError
from tpt import private_settings
import logging

logger = logging.getLogger(__name__)

def create_user(user_name):

    secret_access_key = None
    access_key_id = None

    iam = boto.connect_iam(
            aws_access_key_id = private_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = private_settings.AWS_SECRET_ACCESS_KEY)

    try:
        response = iam.create_user(user_name = user_name)

        iam.add_user_to_group(private_settings.AWS_IAM_GROUP, user_name)

        response = iam.create_access_key(user_name = user_name)

        access_key = response.create_access_key_response.create_access_key_result.access_key

        secret_access_key = access_key.secret_access_key
        access_key_id = access_key.access_key_id

        logger.info('Created iam user "{}"'.format(user_name))

        return {'secret_access_key': secret_access_key,
            'access_key_id': access_key_id,
            'user_name': user_name}

    except BotoServerError, e:
        logger.error('Unable to create iam user "{}": {}, {}'.format(user_name,
            e.status, e.reason))
        raise Exception('iam create error') 


def delete_user(user_name, access_key_id):

    deleted = False

    iam = boto.connect_iam(
            aws_access_key_id = private_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = private_settings.AWS_SECRET_ACCESS_KEY)

    try:
        # Must remove access key and groups from user before deleting
        iam.delete_access_key(access_key_id = access_key_id, user_name = user_name)

        groups = iam.get_groups_for_user(user_name = user_name)
        for group in groups['list_groups_for_user_response']['list_groups_for_user_result']['groups']:
            iam.remove_user_from_group(group_name = group['group_name'], user_name = user_name)

        iam.delete_user(user_name = user_name)

        logger.info('Deleted iam user "{}"'.format(user_name))

        deleted = True

    except BotoServerError, e:
        if e.status == 404:
            logger.error('Trying to delete the iam user "{}", but it ' +\
                    'doesn\'t exist.'.format(user_name))
            deleted = True
        else:
            logger.error('Unable to delete iam user "{}": {}, {}'.
                format(user_name, e.status, e.reason))

    return deleted

