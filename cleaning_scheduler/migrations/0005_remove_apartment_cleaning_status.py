# Generated by Django 4.2.9 on 2024-01-31 14:11

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cleaning_scheduler", "0004_remove_cleaningschedule_apartment"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="apartment",
            name="cleaning_status",
        ),
    ]
