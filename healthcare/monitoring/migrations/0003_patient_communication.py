from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0002_healthcare_upgrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensordata',
            name='movement_request',
            field=models.CharField(default='NONE', max_length=30),
        ),
        migrations.AddField(
            model_name='sensordata',
            name='patient_request',
            field=models.CharField(default='NONE', max_length=30),
        ),
        migrations.AlterField(
            model_name='alert',
            name='alert_type',
            field=models.CharField(
                choices=[
                    ('HIGH_TEMPERATURE', 'High Temperature'),
                    ('EMERGENCY', 'Emergency Button'),
                    ('PATIENT_WATER', 'Water Request'),
                    ('PATIENT_FOOD', 'Food Request'),
                    ('PATIENT_MEDICINE', 'Medicine Request'),
                    ('PATIENT_ASSISTANCE', 'Assistance Request'),
                    ('DEVICE_OFFLINE', 'Device Offline'),
                    ('NO_DATA', 'No Recent Data'),
                ],
                max_length=30,
            ),
        ),
    ]
