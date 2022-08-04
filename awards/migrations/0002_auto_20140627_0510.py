# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0001_initial'),
        ('awards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='nomination',
            name='fic',
            field=models.ForeignKey(blank=True, to='forum.Fic', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='nomination',
            name='member',
            field=models.ForeignKey(to='forum.Member', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='nomination',
            name='nominee',
            field=models.ForeignKey(blank=True, to='forum.Member', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(default=2013, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2013)])),
                ('award', models.ForeignKey(to='awards.Award', on_delete=models.CASCADE)),
                ('member', models.ForeignKey(to='forum.Member', on_delete=models.CASCADE)),
                ('nomination', models.ForeignKey(to='awards.Nomination', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='vote',
            unique_together=set([('member', 'award', 'year')]),
        ),
        migrations.CreateModel(
            name='YearAwards',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(default=2013, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2013)])),
                ('award', models.ForeignKey(to='awards.Award', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('-year', 'award__category', 'award__display_order'),
                'verbose_name_plural': 'Year awards',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='yearawards',
            unique_together=set([('year', 'award')]),
        ),
    ]
