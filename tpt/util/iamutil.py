import boto
from tpt import private_settings

def create_iam_user(user_name):

    secret_access_key = None
    access_key_id = None

    iam = boto.connect_iam(
            aws_access_key_id = private_settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key = private_settings.AWS_SECRET_ACCESS_KEY)

    response = iam.create_user(user_name = user_name)

    if response:
        iam.add_user_to_group(private_settings.AWS_IAM_GROUP, user_name)

        response = iam.create_access_key(user_name = user_name)

        access_key = response.create_access_key_response.create_access_key_result.access_key

        secret_access_key = access_key.secret_access_key
        access_key_id = access_key.access_key_id

    return {'secret_access_key': secret_access_key,
            'access_key_id': access_key_id,
            'user_name': user_name}
