# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0011_auto_20161231_2127'),
    ]

    operations = [
        migrations.AddField(
            model_name='nomination',
            name='verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='vote',
            name='verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='ficeligibility',
            name='year',
            field=models.PositiveIntegerField(default=2017, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2017)]),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='year',
            field=models.PositiveIntegerField(default=2017, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2017)]),
        ),
        migrations.AlterField(
            model_name='vote',
            name='year',
            field=models.PositiveIntegerField(default=2017, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2017)]),
        ),
        migrations.AlterField(
            model_name='yearaward',
            name='year',
            field=models.PositiveIntegerField(default=2017, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2017)]),
        ),
    ]
