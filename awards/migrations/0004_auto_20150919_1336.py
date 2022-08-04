# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0003_auto_20150919_1330'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='yearaward',
            options={'ordering': ('-year', 'award__category', 'award__display_order')},
        ),
        migrations.AlterField(
            model_name='nomination',
            name='award',
            field=models.ForeignKey(related_name='nominations', to='awards.Award', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='fic',
            field=models.ForeignKey(related_name='nominations', blank=True, to='forum.Fic', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='member',
            field=models.ForeignKey(related_name='nominations_by', to='forum.Member', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='nominee',
            field=models.ForeignKey(related_name='nominations', blank=True, to='forum.Member', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='nomination',
            name='year',
            field=models.PositiveIntegerField(default=2015, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2015)]),
        ),
        migrations.AlterField(
            model_name='vote',
            name='award',
            field=models.ForeignKey(related_name='votes', to='awards.Award', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='vote',
            name='member',
            field=models.ForeignKey(related_name='votes', to='forum.Member', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='vote',
            name='nomination',
            field=models.ForeignKey(related_name='votes', to='awards.Nomination', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='vote',
            name='year',
            field=models.PositiveIntegerField(default=2015, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2015)]),
        ),
        migrations.AlterField(
            model_name='yearaward',
            name='year',
            field=models.PositiveIntegerField(default=2015, db_index=True, validators=[django.core.validators.MinValueValidator(2008), django.core.validators.MaxValueValidator(2015)]),
        ),
    ]
