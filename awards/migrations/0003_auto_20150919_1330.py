# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0002_auto_20140627_0510'),
    ]

    operations = [
        migrations.RenameModel('YearAwards', 'YearAward')
    ]
