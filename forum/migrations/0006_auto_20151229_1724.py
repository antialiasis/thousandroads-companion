# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_posted_dates(apps, schema_editor):
    Fic = apps.get_model('forum', 'Fic')
    for fic in Fic.objects.filter(posted_date__isnull=True):
        page = fic.get_page()

        fic.posted_date = page.get_post().posted_date
        fic.save()


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0005_fic_posted_date'),
    ]

    operations = [
        migrations.RunPython(add_posted_dates)
    ]
