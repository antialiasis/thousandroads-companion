# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0006_auto_20151226_0448'),
    ]

    operations = [
        migrations.AddField(
            model_name='nomination',
            name='modified_date',
            field=models.DateTimeField(default=datetime.datetime(2015, 12, 27, 5, 44, 12, 20000, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
