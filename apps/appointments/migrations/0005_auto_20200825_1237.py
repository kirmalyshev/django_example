# Generated by Django 2.2.7 on 2020-08-25 10:37

from django.db import migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0004_auto_20200507_1817'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='created',
            field=model_utils.fields.AutoCreatedField(db_index=True, default=django.utils.timezone.now, editable=False, verbose_name='created'),
        ),
    ]
