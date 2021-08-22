# Generated by Django 3.1.7 on 2021-05-05 11:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0012_auto_20210216_2339'),
        ('appointments', '0007_auto_20210224_1354'),
    ]

    operations = [
        migrations.RenameField(
            model_name='appointment',
            old_name='created_by',
            new_name='created_by_type',
        ),
        migrations.AddField(
            model_name='appointment',
            name='author_patient',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='created_appointments', to='clinics.patient', verbose_name='пациент-создатель'),
        ),
    ]