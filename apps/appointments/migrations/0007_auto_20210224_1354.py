# Generated by Django 3.1.6 on 2021-02-24 11:54

import ckeditor.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0006_auto_20210116_2318'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='additional_notes',
            field=ckeditor.fields.RichTextField(blank=True, help_text='дополнительная информация, которую нужно знать пациенту о приеме. Указывать в виде маркированного списка', null=True, verbose_name='пометки'),
        ),
        migrations.AddField(
            model_name='appointment',
            name='is_for_whole_day',
            field=models.BooleanField(default=False, verbose_name='в течение дня?'),
        ),
    ]
