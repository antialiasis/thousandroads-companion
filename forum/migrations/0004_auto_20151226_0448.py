# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0003_auto_20150919_1935'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fic',
            name='authors',
            field=models.ManyToManyField(related_name='fics', to='forum.Member'),
        ),
    ]
