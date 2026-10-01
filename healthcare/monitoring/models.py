from django.db import models


class Doctor(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Patient(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    phone = models.CharField(max_length=15)

    # New fields (kept optional so existing rows keep working without a data migration)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    medical_notes = models.TextField(blank=True, null=True)
    device_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


class SensorData(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='sensor_readings')

    temperature = models.FloatField()
    humidity = models.FloatField(blank=True, null=True)  # stored for future use, not shown as a health card

    accel_x = models.FloatField()
    accel_y = models.FloatField()
    accel_z = models.FloatField()

    # existing gesture/communication status (FOOD / WATER / SLEEP / EMERGENCY / NORMAL)
    status = models.CharField(max_length=50)

    # plain movement classification required by the monitoring UI
    movement_status = models.CharField(max_length=30, default='NORMAL')

    high_temperature = models.BooleanField(default=False)
    emergency = models.BooleanField(default=False)  # from the physical emergency button (GPIO 26)
    movement_request = models.CharField(max_length=30, default='NONE')
    patient_request = models.CharField(max_length=30, default='NONE')

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.patient.name} @ {self.timestamp:%H:%M:%S}"


class Device(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='device')
    device_id = models.CharField(max_length=50, blank=True, null=True)
    last_seen = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.device_id or f"device-{self.patient_id}"


class Alert(models.Model):
    TYPE_CHOICES = [
        ('HIGH_TEMPERATURE', 'High Temperature'),
        ('EMERGENCY', 'Emergency Button'),
        ('PATIENT_WATER', 'Water Request'),
        ('PATIENT_FOOD', 'Food Request'),
        ('PATIENT_MEDICINE', 'Medicine Request'),
        ('PATIENT_ASSISTANCE', 'Assistance Request'),
        ('DEVICE_OFFLINE', 'Device Offline'),
        ('NO_DATA', 'No Recent Data'),
    ]
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('WARNING', 'Warning'),
        ('INFO', 'Information'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='WARNING')
    value = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.patient.name}"
