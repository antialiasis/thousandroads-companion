# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0004_auto_20150919_1336'),
    ]

    operations = [
        migrations.AddField(
            model_name='award',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
