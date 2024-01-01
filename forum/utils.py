import bbcode
from django.conf import settings


bbcode_formatter = bbcode.Parser()
bbcode_formatter.add_simple_formatter('spoiler', '<span class="spoiler" title="Click to reveal">%(value)s</span>')


def bbcode_to_html(text):
    return bbcode_formatter.format(text)

def forum_url_from_path(path):
    return "https://{}{}".format(settings.FORUM_URL.rsplit('/', 1)[0], path)
