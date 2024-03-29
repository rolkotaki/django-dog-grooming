# Generated by Django 4.2.5 on 2023-10-13 07:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dog_grooming_app', '0004_contact_google_maps_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('dog_size', models.CharField()),
                ('service_price', models.IntegerField(null=True)),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('comment', models.TextField()),
                ('cancelled', models.BooleanField(default=False)),
                ('booking_date', models.DateTimeField(auto_now=True)),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='dog_grooming_app.service')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
