import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='gender',
            field=models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='patient',
            name='medical_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='patient',
            name='device_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='sensordata',
            name='humidity',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sensordata',
            name='movement_status',
            field=models.CharField(default='NORMAL', max_length=30),
        ),
        migrations.AddField(
            model_name='sensordata',
            name='high_temperature',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sensordata',
            name='emergency',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name='sensordata',
            options={'ordering': ['-timestamp']},
        ),
        migrations.AlterField(
            model_name='sensordata',
            name='patient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sensor_readings', to='monitoring.patient'),
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(blank=True, max_length=50, null=True)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('patient', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='device', to='monitoring.patient')),
            ],
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_type', models.CharField(choices=[('HIGH_TEMPERATURE', 'High Temperature'), ('EMERGENCY', 'Emergency Button'), ('DEVICE_OFFLINE', 'Device Offline'), ('NO_DATA', 'No Recent Data')], max_length=30)),
                ('severity', models.CharField(choices=[('CRITICAL', 'Critical'), ('WARNING', 'Warning'), ('INFO', 'Information')], default='WARNING', max_length=10)),
                ('value', models.CharField(blank=True, max_length=50, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('acknowledged', models.BooleanField(default=False)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='monitoring.patient')),
            ],
            options={'ordering': ['-timestamp']},
        ),
    ]
