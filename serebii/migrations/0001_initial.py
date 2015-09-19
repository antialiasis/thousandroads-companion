# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import django.utils.timezone
import serebii.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, max_length=30, verbose_name='username', validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username.', 'invalid')])),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('verified', models.BooleanField(default=False)),
                ('verification_code', models.CharField(default=serebii.models.get_verification_code, max_length=10)),
                ('groups', models.ManyToManyField(to='auth.Group', verbose_name='groups', blank=True)),
                ('user_permissions', models.ManyToManyField(to='auth.Permission', verbose_name='user permissions', blank=True)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Fic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('thread_id', models.PositiveIntegerField()),
                ('post_id', models.PositiveIntegerField(null=True, blank=True)),
            ],
            options={
                'ordering': [b'title', b'thread_id', b'post_id'],
            },
            bases=(serebii.models.SerebiiObject, models.Model),
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('user_id', models.PositiveIntegerField(unique=True, serialize=False, primary_key=True)),
                ('username', models.CharField(max_length=50)),
            ],
            options={
                'ordering': [b'username'],
            },
            bases=(serebii.models.SerebiiObject, models.Model),
        ),
        migrations.AddField(
            model_name='fic',
            name='authors',
            field=models.ManyToManyField(to='serebii.Member'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='fic',
            unique_together=set([(b'thread_id', b'post_id')]),
        ),
        migrations.AddField(
            model_name='user',
            name='member',
            field=models.ForeignKey(blank=True, to='serebii.Member', null=True),
            preserve_default=True,
        ),
    ]
