# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0008_auto_20151227_0607'),
    ]

    operations = [
        migrations.AddField(
            model_name='award',
            name='requires_new',
            field=models.BooleanField(default=False),
        ),
    ]
