from django.contrib import admin
from .models import Doctor, Patient, SensorData, Device, Alert

admin.site.register(Doctor)
admin.site.register(Patient)
admin.site.register(SensorData)
admin.site.register(Device)
admin.site.register(Alert)
