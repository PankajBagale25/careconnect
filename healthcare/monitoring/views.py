from datetime import timedelta

from django.conf import settings
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Doctor, Patient, SensorData, Device, Alert

# A device with no reading in this many seconds is considered OFFLINE.
DEVICE_OFFLINE_SECONDS = getattr(settings, 'DEVICE_OFFLINE_SECONDS', 30)
HIGH_TEMP_THRESHOLD = 38.0


# =======================================================================
# PAGES
# =======================================================================

def login_page(request):
    return render(request, 'login.html')


def logout_user(request):
    return redirect('/')


@csrf_exempt  # NOTE: for production, remove this and post the CSRF token instead
def login_user(request):
    if request.method == "POST":
        role = request.POST.get('role')
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        if role == "doctor":
            doctor = Doctor.objects.filter(phone=phone, password=password).first()
            if doctor:
                return redirect(f'/doctor/?id={doctor.id}')
            return render(request, 'login.html', {"error": "Invalid doctor credentials", "role": role})

        elif role == "patient":
            patient = Patient.objects.filter(phone=phone).first()
            if patient:
                return redirect(f'/dashboard/?id={patient.id}')
            return render(request, 'login.html', {"error": "Patient not found", "role": role})

        return render(request, 'login.html', {"error": "Please choose a role", "role": role})

    return redirect('/')


def dashboard(request):
    """Patient monitoring page (the main highlight of the app)."""
    patient_id = request.GET.get('id')
    return render(request, 'dashboard.html', {"patient_id": patient_id})


def doctor_dashboard(request):
    doctor_id = request.GET.get('id')
    return render(request, 'doctor_dashboard.html', {"doctor_id": doctor_id})


def alerts_page(request):
    doctor_id = request.GET.get('id')
    return render(request, 'alerts.html', {"doctor_id": doctor_id})


def reports_page(request):
    doctor_id = request.GET.get('id')
    return render(request, 'reports.html', {"doctor_id": doctor_id})


def settings_page(request):
    doctor_id = request.GET.get('id')
    return render(request, 'settings.html', {
        "doctor_id": doctor_id,
        "poll_interval_ms": getattr(settings, 'FRONTEND_POLL_INTERVAL_MS', 3000),
        "high_temp_threshold": getattr(settings, 'HIGH_TEMP_THRESHOLD', 38.0),
    })


def patient_profile_page(request):
    patient_id = request.GET.get('id')
    doctor_id = request.GET.get('doctor_id')
    return render(request, 'patient_profile.html', {"patient_id": patient_id, "doctor_id": doctor_id})


# =======================================================================
# HELPERS
# =======================================================================

def _device_status_for(patient):
    device = getattr(patient, 'device', None)
    if not device or not device.last_seen:
        return "DISCONNECTED", None
    seconds_ago = (timezone.now() - device.last_seen).total_seconds()
    if seconds_ago <= DEVICE_OFFLINE_SECONDS:
        return "CONNECTED", device.last_seen
    return "DISCONNECTED", device.last_seen


def _classify_movement(ax, ay, az):
    """Simple magnitude-based movement classification for the Movement card."""
    magnitude = (ax ** 2 + ay ** 2 + az ** 2) ** 0.5
    # ~1g at rest for a stationary MPU6050; flag meaningful deviation as movement
    if abs(magnitude - 1.0) > 0.3 or abs(magnitude) > 1.3:
        return "MOVEMENT_DETECTED"
    return "NORMAL"


def _maybe_create_alert(patient, alert_type, severity, value):
    """Avoid spamming duplicate alerts for the same ongoing condition."""
    recent_cutoff = timezone.now() - timedelta(minutes=5)
    existing = Alert.objects.filter(
        patient=patient, alert_type=alert_type, acknowledged=False, timestamp__gte=recent_cutoff
    ).first()
    if existing:
        return existing
    return Alert.objects.create(
        patient=patient, alert_type=alert_type, severity=severity, value=value
    )


def _serialize_alert(a):
    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "patient_name": a.patient.name,
        "type": a.alert_type,
        "type_display": a.get_alert_type_display(),
        "value": a.value,
        "severity": a.severity,
        "date": a.timestamp.strftime("%Y-%m-%d"),
        "time": a.timestamp.strftime("%H:%M:%S"),
        "acknowledged": a.acknowledged,
    }


# =======================================================================
# API - INGEST (called by the ESP32)
# =======================================================================

@api_view(['POST'])
def save_data(request):
    try:
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({"error": "Patient ID required"}, status=400)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)

        temp = float(request.data.get('temperature', 0))
        humidity_raw = request.data.get('humidity', None)
        humidity = float(humidity_raw) if humidity_raw not in (None, '') else None

        ax = float(request.data.get('ax', 0))
        ay = float(request.data.get('ay', 0))
        az = float(request.data.get('az', 0))

        emergency = str(request.data.get('emergency', False)).lower() in ('true', '1', 'yes')

        # Existing MPU6050 communication is preserved.
        if ax > 7:
            movement_request = "FOOD"
        elif ay > 7:
            movement_request = "WATER"
        elif az > 9:
            movement_request = "EMERGENCY"
        elif ax < -7:
            movement_request = "SLEEP"
        else:
            movement_request = "NONE"

        # Push-button communication from ESP32:
        # 1 press = EMERGENCY, 2 = WATER, 3 = FOOD, 4 = MEDICINE.
        patient_request = str(request.data.get('patient_request', 'NONE')).upper()
        allowed_requests = {"NONE", "EMERGENCY", "WATER", "FOOD", "MEDICINE"}
        if patient_request not in allowed_requests:
            patient_request = "NONE"

        movement_status = _classify_movement(ax, ay, az)
        high_temperature = temp >= HIGH_TEMP_THRESHOLD

        if patient_request == "EMERGENCY":
            emergency = True

        # Keep status backward-compatible with the existing MPU6050 feature.
        status = movement_request if movement_request != "NONE" else "NORMAL"

        SensorData.objects.create(
            patient=patient,
            temperature=temp,
            humidity=humidity,
            accel_x=ax,
            accel_y=ay,
            accel_z=az,
            status=status,
            movement_status=movement_status,
            high_temperature=high_temperature,
            emergency=emergency,
            movement_request=movement_request,
            patient_request=patient_request,
        )

        # ===== Device heartbeat =====
        device, _ = Device.objects.get_or_create(patient=patient)
        incoming_device_id = request.data.get('device_id')
        if incoming_device_id:
            device.device_id = incoming_device_id
        device.last_seen = timezone.now()
        device.save()

        # ===== Alerts =====
        if high_temperature:
            _maybe_create_alert(patient, 'HIGH_TEMPERATURE', 'CRITICAL' if temp >= 39 else 'WARNING', f"{temp:.1f}\u00b0C")
        if emergency:
            _maybe_create_alert(patient, 'EMERGENCY', 'CRITICAL', "Emergency button pressed")

        request_alerts = {
            "WATER": ("PATIENT_WATER", "INFO", "Patient requested water"),
            "FOOD": ("PATIENT_FOOD", "INFO", "Patient requested food"),
            "MEDICINE": ("PATIENT_MEDICINE", "WARNING", "Patient requested medicine"),
        }
        if patient_request in request_alerts:
            alert_type, severity, message = request_alerts[patient_request]
            Alert.objects.create(
                patient=patient,
                alert_type=alert_type,
                severity=severity,
                value=message,
            )

        return Response({
            "message": "Data saved",
            "status": status,
            "movement_status": movement_status,
            "high_temperature": high_temperature,
            "emergency": emergency,
            "movement_request": movement_request,
            "patient_request": patient_request,
        })

    except Exception as e:
        return Response({"error": str(e)}, status=400)


# =======================================================================
# API - PATIENT DATA
# =======================================================================

@api_view(['GET'])
def patient_data(request, patient_id):
    """Temperature history for the monitoring chart."""
    try:
        limit = int(request.GET.get('limit', 30))
    except ValueError:
        limit = 30

    readings = SensorData.objects.filter(patient_id=patient_id)[:limit]

    response = []
    for d in readings:
        response.append({
            "temp": d.temperature,
            "high_temperature": d.high_temperature,
            "status": d.status,
            "movement_status": d.movement_status,
            "movement_request": d.movement_request,
            "patient_request": d.patient_request,
            "time": d.timestamp.strftime("%H:%M:%S"),
            "date": d.timestamp.strftime("%Y-%m-%d"),
        })

    return Response(response[::-1])


@api_view(['GET'])
def patient_latest(request, patient_id):
    """Everything the monitoring page needs for one poll cycle."""
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)

    latest = SensorData.objects.filter(patient=patient).first()
    recent = list(SensorData.objects.filter(patient=patient)[:50])

    device_status, last_seen = _device_status_for(patient)

    temps = [r.temperature for r in recent]
    stats = None
    if temps:
        stats = {
            "current": temps[0],
            "min": min(temps),
            "max": max(temps),
            "avg": round(sum(temps) / len(temps), 1),
        }

    unacknowledged = Alert.objects.filter(patient=patient, acknowledged=False).count()

    return Response({
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
        },
        "device_status": device_status,
        "last_seen": last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else None,
        "latest": None if not latest else {
            "temperature": latest.temperature,
            "high_temperature": latest.high_temperature,
            "emergency": latest.emergency,
            "movement_request": latest.movement_request,
            "patient_request": latest.patient_request,
            "accel_x": latest.accel_x,
            "accel_y": latest.accel_y,
            "accel_z": latest.accel_z,
            "movement_status": latest.movement_status,
            "status": latest.status,
            "time": latest.timestamp.strftime("%H:%M:%S"),
        },
        "temperature_stats": stats,
        "unacknowledged_alerts": unacknowledged,
    })


@api_view(['GET'])
def patient_profile_data(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)

    device_status, last_seen = _device_status_for(patient)
    device = getattr(patient, 'device', None)

    recent_alerts = Alert.objects.filter(patient=patient)[:10]
    history = SensorData.objects.filter(patient=patient)[:20]

    return Response({
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "phone": patient.phone,
            "medical_notes": patient.medical_notes,
            "device_id": device.device_id if device else patient.device_id,
            "doctor_name": patient.doctor.name,
        },
        "device_status": device_status,
        "last_seen": last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else None,
        "alerts": [_serialize_alert(a) for a in recent_alerts],
        "temperature_history": [
            {"time": d.timestamp.strftime("%H:%M:%S"), "temp": d.temperature} for d in reversed(history)
        ],
    })


# =======================================================================
# API - DOCTOR
# =======================================================================

@api_view(['POST'])
def add_patient(request):
    try:
        doctor_id = request.data.get('doctor_id')
        name = request.data.get('name')
        age = request.data.get('age')
        phone = request.data.get('phone')
        gender = request.data.get('gender') or None
        medical_notes = request.data.get('medical_notes') or None
        device_id = request.data.get('device_id') or None

        if not doctor_id or not name or not phone:
            return Response({"error": "Missing required fields"}, status=400)

        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=404)

        patient = Patient.objects.create(
            doctor=doctor, name=name, age=age, phone=phone,
            gender=gender, medical_notes=medical_notes, device_id=device_id,
        )
        Device.objects.get_or_create(patient=patient, defaults={"device_id": device_id})

        return Response({"message": "Patient added", "id": patient.id})

    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
def doctor_patients(request, doctor_id):
    try:
        patients = Patient.objects.filter(doctor_id=doctor_id)

        data = []
        for p in patients:
            device_status, last_seen = _device_status_for(p)
            latest = SensorData.objects.filter(patient=p).first()
            has_alert = Alert.objects.filter(patient=p, acknowledged=False).exists()

            data.append({
                "id": p.id,
                "name": p.name,
                "age": p.age,
                "gender": p.gender,
                "phone": p.phone,
                "device_status": device_status,
                "latest_temperature": latest.temperature if latest else None,
                "condition": latest.movement_status if latest else "NO_DATA",
                "last_update": latest.timestamp.strftime("%H:%M:%S") if latest else None,
                "has_alert": has_alert or (latest.high_temperature if latest else False) or (latest.emergency if latest else False),
            })

        return Response(data)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
def doctor_overview(request, doctor_id):
    patients = Patient.objects.filter(doctor_id=doctor_id)
    total = patients.count()

    active = 0
    attention = 0
    connected_devices = 0

    for p in patients:
        status, _ = _device_status_for(p)
        if status == "CONNECTED":
            active += 1
            connected_devices += 1
        if Alert.objects.filter(patient=p, acknowledged=False).exists():
            attention += 1

    return Response({
        "total_patients": total,
        "active_patients": active,
        "attention_required": attention,
        "connected_devices": connected_devices,
    })


@api_view(['GET'])
def alerts_list(request, doctor_id):
    patients = Patient.objects.filter(doctor_id=doctor_id)
    alerts = Alert.objects.filter(patient__in=patients)

    patient_filter = request.GET.get('patient_id')
    if patient_filter:
        alerts = alerts.filter(patient_id=patient_filter)

    type_filter = request.GET.get('type')
    if type_filter:
        alerts = alerts.filter(alert_type=type_filter)

    date_filter = request.GET.get('date')
    if date_filter:
        alerts = alerts.filter(timestamp__date=date_filter)

    alerts = alerts[:200]
    return Response([_serialize_alert(a) for a in alerts])


@api_view(['POST'])
def acknowledge_alert(request, alert_id):
    try:
        alert = Alert.objects.get(id=alert_id)
        alert.acknowledged = True
        alert.save()
        return Response({"message": "Alert acknowledged"})
    except Alert.DoesNotExist:
        return Response({"error": "Alert not found"}, status=404)


@api_view(['GET'])
def device_status_api(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)

    status, last_seen = _device_status_for(patient)
    latest = SensorData.objects.filter(patient=patient).first()
    device = getattr(patient, 'device', None)

    return Response({
        "device_id": (device.device_id if device else patient.device_id) or "-",
        "status": status,
        "last_seen": last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else None,
        "last_temperature": latest.temperature if latest else None,
        "last_movement": latest.movement_status if latest else None,
    })


@api_view(['GET'])
def reports_data(request, doctor_id):
    patients = Patient.objects.filter(doctor_id=doctor_id)

    patient_filter = request.GET.get('patient_id')
    if patient_filter:
        patients = patients.filter(id=patient_filter)

    readings = SensorData.objects.filter(patient__in=patients)
    alerts = Alert.objects.filter(patient__in=patients)

    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    if date_from:
        readings = readings.filter(timestamp__date__gte=date_from)
        alerts = alerts.filter(timestamp__date__gte=date_from)
    if date_to:
        readings = readings.filter(timestamp__date__lte=date_to)
        alerts = alerts.filter(timestamp__date__lte=date_to)

    high_temp_events = alerts.filter(alert_type='HIGH_TEMPERATURE').count()
    emergency_events = alerts.filter(alert_type='EMERGENCY').count()

    connected = sum(1 for p in patients if _device_status_for(p)[0] == "CONNECTED")
    uptime_pct = round((connected / patients.count()) * 100, 1) if patients.count() else 0

    chart = list(readings.order_by('timestamp')[:100].values_list('timestamp', 'temperature'))
    chart_data = [{"time": t.strftime("%Y-%m-%d %H:%M"), "temp": temp} for t, temp in chart]

    return Response({
        "high_temperature_events": high_temp_events,
        "emergency_events": emergency_events,
        "device_uptime_percent": uptime_pct,
        "total_readings": readings.count(),
        "temperature_history": chart_data,
    })
