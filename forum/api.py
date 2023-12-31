from django.conf import settings
import requests

def make_api_request(method, endpoint, payload=None, params=None):
    resp = requests.request(
        method,
        'https://%sapi/%s' % (settings.FORUM_URL, endpoint),
        params=params,
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


def get_user_threads(user_id, page=1):
    return make_api_request('GET', 'threads', params={'starter_id': user_id, 'page': page})


class ThreadAPIIterator:
    page = None
    page_posts = None
    index = None

    def __init__(self, thread_id):
        self.thread_id = thread_id
        self.page = 0
        self.response = {'posts': [], 'pagination': {'last_page': 1}}
        self.index = 0

    def __next__(self):
        if self.index >= len(self.response['posts']):
            if self.page >= self.response['pagination']['last_page']:
                raise StopIteration

            self.page += 1
            try:
                self.response = make_api_request('GET', 'threads/%s/posts' % self.thread_id, params={'page': self.page})
            except Exception:
                raise StopIteration
            if not self.response.get('posts'):
                raise StopIteration
            self.index = 0
        post = self.response['posts'][self.index]
        self.index += 1
        return post


class ThreadPosts:
    def __init__(self, thread_id):
        self.thread_id = thread_id

    def __iter__(self):
        return ThreadAPIIterator(self.thread_id)


def get_thread_posts(thread_id):
    return ThreadPosts(thread_id)
