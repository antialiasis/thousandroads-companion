# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('serebii', '0006_auto_20151229_1724'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fic',
            name='posted_date',
            field=models.DateTimeField(),
        ),
    ]
