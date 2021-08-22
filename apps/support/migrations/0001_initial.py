# Generated by Django 2.2.7 on 2020-03-03 14:11

import ckeditor.fields
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
            name='FrequentQuestion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_displayed', models.BooleanField(db_index=True, default=True, verbose_name='отображается?')),
                ('question', ckeditor.fields.RichTextField(help_text='', verbose_name='Вопрос')),
                ('answer', ckeditor.fields.RichTextField(help_text='', verbose_name='Ответ')),
            ],
            options={
                'verbose_name': 'Часто задаваемый вопрос',
                'verbose_name_plural': 'Часто задаваемые вопросы',
            },
        ),
        migrations.CreateModel(
            name='SupportRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(blank=True, max_length=300, null=True, verbose_name='Email')),
                ('phone', models.CharField(blank=True, max_length=300, null=True, verbose_name='Телефон')),
                ('text', models.TextField(verbose_name='Текст')),
                ('is_processed', models.BooleanField(default=False, verbose_name='Обработано?')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Обращение в саппорт',
                'verbose_name_plural': 'Обращения в саппорт',
            },
        ),
    ]
