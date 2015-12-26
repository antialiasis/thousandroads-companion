# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0005_award_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='FicEligibility',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(default=2015, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2015)])),
                ('thread_id', models.PositiveIntegerField()),
                ('post_id', models.PositiveIntegerField(null=True, blank=True)),
                ('is_eligible', models.BooleanField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='ficeligibility',
            unique_together=set([('thread_id', 'post_id', 'year')]),
        ),
    ]
