# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def mark_verified(apps, schema_editor):
    Nomination = apps.get_model('awards', 'Nomination')
    Vote = apps.get_model('awards', 'Vote')

    Nomination.objects.filter(year__lt=2014).update(verified=True)
    Vote.objects.filter(year__lt=2014).update(verified=True)

    Nomination.objects.filter(year__gte=2014, member__user__verified=True).update(verified=True)
    Vote.objects.filter(year__gte=2014, member__user__verified=True).update(verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0012_auto_20180111_0255'),
    ]

    operations = [
        migrations.RunPython(mark_verified)
    ]
