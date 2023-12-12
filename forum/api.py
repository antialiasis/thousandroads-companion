from django.conf import settings
import requests

def make_api_request(method, endpoint, payload=None):
    resp = requests.request(
        method,
        'https://%s/api/%s' % (settings.FORUM_URL, endpoint),
        data=payload,
        headers={
            'XF-Api-Key': settings.FORUM_API_KEY,
            'XF-Api-User': '1'
        }
    )

    return resp.json()

def add_user_to_group(user_id, group_id):
    try:
        user_data = make_api_request('GET', 'users/%s' % user_id)

        groups = user_data['user']['secondary_group_ids']
        if group_id not in groups:
            groups.append(group_id)
            # Must use tuples for PHP array format
            payload = [('secondary_group_ids[]', str(group_id)) for group_id in groups]
            resp = make_api_request('POST', 'users/%s' % user_id, payload)
            return resp.get('success')
    except Exception as e:
        return False
    return True


def get_user_info(user_id):
    try:
        user_data = make_api_request('GET', 'users/%s' % user_id)
    except Exception as e:
        return (None, None)
    else:
        return (user_data['user']['username'], user_data['user']['custom_fields'].get('verificationcode', ''))
