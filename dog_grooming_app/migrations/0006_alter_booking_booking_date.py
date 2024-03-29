# Generated by Django 4.2.5 on 2023-10-13 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dog_grooming_app', '0005_booking'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='booking_date',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='dog_size',
            field=models.CharField(null=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='service_price',
            field=models.IntegerField(),
        ),
    ]
