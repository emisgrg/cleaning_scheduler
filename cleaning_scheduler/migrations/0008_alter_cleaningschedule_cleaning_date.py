# Generated by Django 4.2.9 on 2024-02-01 09:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cleaning_scheduler", "0007_cleaningschedule_window_end_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cleaningschedule",
            name="cleaning_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
