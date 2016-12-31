# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0009_award_requires_new'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ficeligibility',
            options={'verbose_name_plural': 'fic eligibilities'},
        ),
        migrations.AddField(
            model_name='award',
            name='detail_character_limit',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='ficeligibility',
            name='year',
            field=models.PositiveIntegerField(default=2016, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2016)]),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='year',
            field=models.PositiveIntegerField(default=2016, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2016)]),
        ),
        migrations.AlterField(
            model_name='vote',
            name='year',
            field=models.PositiveIntegerField(default=2016, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2016)]),
        ),
        migrations.AlterField(
            model_name='yearaward',
            name='year',
            field=models.PositiveIntegerField(default=2016, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2016)]),
        ),
    ]
