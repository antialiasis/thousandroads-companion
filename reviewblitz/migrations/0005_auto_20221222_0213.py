# Generated by Django 2.2.28 on 2022-12-22 02:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0013_chapter'),
        ('reviewblitz', '0004_auto_20221127_1554'),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewblitzscoring',
            name='long_chapter_bonus',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=3),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reviewblitzscoring',
            name='long_chapter_bonus_words',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='ReviewChapterLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chapter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='forum.Chapter')),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chapter_links', to='reviewblitz.BlitzReview')),
            ],
        ),
    ]