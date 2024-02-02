# Generated by Django 4.2.9 on 2024-01-24 12:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cleaning_scheduler", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_name", models.CharField(max_length=100)),
                ("check_in_date", models.DateField()),
                ("check_out_date", models.DateField()),
                (
                    "apartment",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cleaning_scheduler.apartment"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CleaningSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cleaning_date", models.DateField()),
                (
                    "apartment",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cleaning_scheduler.apartment"),
                ),
                (
                    "booking",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="cleaning_scheduler.booking"),
                ),
            ],
        ),
    ]
