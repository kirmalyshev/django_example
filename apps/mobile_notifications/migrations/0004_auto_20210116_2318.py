# Generated by Django 3.1.5 on 2021-01-16 21:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mobile_notifications', '0003_pushlog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pushlog',
            name='data',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='data'),
        ),
    ]