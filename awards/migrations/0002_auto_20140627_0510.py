# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('serebii', '0001_initial'),
        ('awards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nomination',
            name='fic',
            field=models.ForeignKey(blank=True, to='serebii.Fic', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='nomination',
            name='member',
            field=models.ForeignKey(to='serebii.Member'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='nomination',
            name='nominee',
            field=models.ForeignKey(blank=True, to='serebii.Member', null=True),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(default=2013, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2013)])),
                ('award', models.ForeignKey(to='awards.Award')),
                ('member', models.ForeignKey(to='serebii.Member')),
                ('nomination', models.ForeignKey(to='awards.Nomination')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set([(b'member', b'award', b'year')]),
        ),
        migrations.CreateModel(
            name='YearAwards',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(default=2013, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2013)])),
                ('award', models.ForeignKey(to='awards.Award')),
            ],
            options={
                'ordering': (b'-year', b'award__category', b'award__display_order'),
                'verbose_name_plural': 'Year awards',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='yearawards',
            unique_together=set([(b'year', b'award')]),
        ),
    ]
