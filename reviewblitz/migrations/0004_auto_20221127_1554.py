# Generated by Django 2.2.28 on 2022-11-27 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviewblitz', '0003_auto_20221118_0424'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blitzreview',
            name='score',
            field=models.DecimalField(decimal_places=2, max_digits=4),
        ),
    ]
