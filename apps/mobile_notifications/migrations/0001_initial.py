# Generated by Django 2.2.7 on 2019-11-28 22:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpoDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Name')),
                ('active', models.BooleanField(default=True, help_text='Inactive devices will not be sent notifications', verbose_name='Is active')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Creation date')),
                ('application_id', models.CharField(blank=True, help_text='Opaque application identity, should be filled in for multiple key/certificate access', max_length=64, null=True, verbose_name='Application ID')),
                ('device_id', models.CharField(blank=True, db_index=True, help_text="Expo token - like 'ExponentPushToken[123456789456]'", max_length=200, null=True, verbose_name='Device ID - Token')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Expo device',
                'verbose_name_plural': 'Expo devices',
            },
        ),
    ]
