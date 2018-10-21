# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Award',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('has_person', models.BooleanField(default=False)),
                ('has_fic', models.BooleanField(default=False)),
                ('has_detail', models.BooleanField(default=False)),
                ('has_samples', models.BooleanField(default=False)),
                ('display_order', models.PositiveIntegerField(blank=True)),
            ],
            options={
                'ordering': ('category', 'display_order', 'pk'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'ordering': ('id',),
                'verbose_name_plural': 'categories',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='award',
            name='category',
            field=models.ForeignKey(to='awards.Category', on_delete=models.PROTECT),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Nomination',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(default=2013, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2013)])),
                ('detail', models.TextField(help_text='The character(s), scene or quote that you want to nominate.', blank=True)),
                ('link', models.URLField(help_text='A link to a sample (generally a post) illustrating your nomination.', null=True, blank=True)),
                ('comment', models.TextField(help_text='Optionally, you may write a comment explaining why you feel this nomination deserves the award. Users will be able to see this on the voting form. Basic BBCode allowed.', blank=True)),
                ('award', models.ForeignKey(to='awards.Award', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
