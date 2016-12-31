# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0010_auto_20161231_2124'),
    ]

    operations = [
        migrations.AlterField(
            model_name='award',
            name='detail_character_limit',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
