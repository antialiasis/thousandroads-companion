# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('serebii', '0004_auto_20151226_0448'),
    ]

    operations = [
        migrations.AddField(
            model_name='fic',
            name='posted_date',
            field=models.DateTimeField(null=True),
        ),
    ]
