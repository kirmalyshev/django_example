# Generated by Django 3.1.7 on 2021-05-06 13:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mobile_notifications', '0004_auto_20210116_2318'),
    ]

    operations = [
        migrations.AddField(
            model_name='pushlog',
            name='appointment_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
