import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Doctor, Patient, SensorData, Device, Alert


class Command(BaseCommand):
    help = "Creates a demo doctor, a demo patient, and sample sensor history for local testing."

    def handle(self, *args, **options):
        doctor, created = Doctor.objects.get_or_create(
            phone="9999999999",
            defaults={"name": "Dr. Asha Verma", "password": "demo1234"},
        )
        if not created:
            doctor.password = "demo1234"
            doctor.name = "Dr. Asha Verma"
            doctor.save()

        patient, _ = Patient.objects.get_or_create(
            phone="8888888888",
            defaults={
                "doctor": doctor,
                "name": "Ramesh Kumar",
                "age": 58,
                "gender": "male",
                "medical_notes": "Post-stroke paralysis, right side. Monitored for fever and movement.",
                "device_id": "ESP32-DEMO-01",
            },
        )

        device, _ = Device.objects.get_or_create(patient=patient, defaults={"device_id": "ESP32-DEMO-01"})
        device.device_id = "ESP32-DEMO-01"
        device.last_seen = timezone.now()
        device.save()

        # Sample sensor history over the last hour, one reading every 5 minutes
        now = timezone.now()
        SensorData.objects.filter(patient=patient).delete()
        Alert.objects.filter(patient=patient).delete()

        for i in range(12, 0, -1):
            ts = now - timedelta(minutes=i * 5)
            is_spike = i in (5, 4)
            temp = round(random.uniform(38.2, 38.7), 1) if is_spike else round(random.uniform(36.2, 37.4), 1)
            reading = SensorData.objects.create(
                patient=patient,
                temperature=temp,
                humidity=round(random.uniform(50, 65), 1),
                accel_x=round(random.uniform(-0.2, 0.2), 3),
                accel_y=round(random.uniform(-0.2, 0.2), 3),
                accel_z=round(random.uniform(0.9, 1.05), 3),
                status="NORMAL",
                movement_status="NORMAL",
                high_temperature=temp >= 38.0,
            )
            reading.timestamp = ts
            reading.save(update_fields=["timestamp"])

            if temp >= 38.0:
                alert = Alert.objects.create(
                    patient=patient, alert_type="HIGH_TEMPERATURE",
                    severity="WARNING", value=f"{temp:.1f}\u00b0C",
                )
                alert.timestamp = ts
                alert.save(update_fields=["timestamp"])

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Doctor login  -> phone: 9999999999  password: demo1234")
        self.stdout.write(f"  Patient login -> phone: 8888888888  (no password required)")
        self.stdout.write(f"  Doctor dashboard: /doctor/?id={doctor.id}")
        self.stdout.write(f"  Patient monitoring: /dashboard/?id={patient.id}")
