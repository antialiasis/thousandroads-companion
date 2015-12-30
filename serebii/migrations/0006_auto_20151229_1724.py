# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import urllib

from django.db import models, migrations
from serebii.models import get_soup, get_post_date


def add_posted_dates(apps, schema_editor):
    Fic = apps.get_model('serebii', 'Fic')
    for fic in Fic.objects.filter(posted_date__isnull=True):
        link_kwargs = {}
        if fic.post_id:
            link_kwargs['p'] = fic.post_id
        else:
            link_kwargs['t'] = fic.thread_id
        soup = get_soup('http://www.serebiiforums.com/showthread.php?%s' % urllib.urlencode(link_kwargs))
        if fic.post_id is not None:
            post = soup.find(id="post_%s" % fic.post_id)
        else:
            post = soup.find(id="posts").li

        fic.posted_date = get_post_date(soup, post)
        fic.save()


class Migration(migrations.Migration):

    dependencies = [
        ('serebii', '0005_fic_posted_date'),
    ]

    operations = [
        migrations.RunPython(add_posted_dates)
    ]
