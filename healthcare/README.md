# CareConnect — IoT-Based Paralysis Patient Healthcare Monitoring System

This is your existing Django project, upgraded in place: same app (`monitoring`), same
database, same URL structure — with a professional CareConnect UI, alerts, device
tracking, reports, and a demo mode layered on top. Nothing was rebuilt from scratch.

> Note: your original request described a React/Tailwind frontend, but the project you
> uploaded is a **Django backend that renders its own HTML templates** (no `frontend/`
> folder, no `package.json`). Rebuilding it in React would mean starting a second,
> separate project. Since you asked me to modify what you already have, everything below
> upgrades the existing Django templates and views instead — same tech stack, much more
> polished, all the features from your spec.

## What changed

- **Models**: added `humidity`, `high_temperature`, `emergency`, `movement_status` to
  `SensorData`; added `gender`, `medical_notes`, `device_id` to `Patient`; added new
  `Device` and `Alert` models. Your original gesture-communication logic
  (FOOD/WATER/SLEEP/EMERGENCY from accelerometer thresholds) is untouched and still runs
  alongside the new features.
- **Views/API**: extended with endpoints for live polling, alerts, device status, doctor
  overview stats, reports, and patient profile (full list below).
- **Templates**: `login.html`, `doctor_dashboard.html`, and `dashboard.html` (patient
  monitoring) were redesigned with a light blue/teal healthcare theme. New pages:
  `alerts.html`, `reports.html`, `patient_profile.html`, plus a shared `base.html` shell
  (sidebar, topbar, dark mode).
- **Static assets**: `static/css/theme.css` and `static/js/app.js` hold the shared design
  system, dark-mode toggle, and the demo-data generator.
- **Settings**: secrets and hosts now come from environment variables / a `.env` file
  instead of being hard-coded.

## Folder structure

```
healthcare/
├── healthcare/            # Django project (settings, urls)
├── monitoring/             # The app
│   ├── models.py           # Doctor, Patient, SensorData, Device, Alert
│   ├── views.py             # Pages + REST API endpoints
│   ├── urls.py
│   ├── context_processors.py
│   ├── management/commands/seed_demo_data.py
│   └── templates/
│       ├── base.html        # Shared sidebar/topbar shell (doctor pages)
│       ├── login.html
│       ├── dashboard.html    # Patient monitoring (the main page)
│       ├── doctor_dashboard.html
│       ├── alerts.html
│       ├── reports.html
│       └── patient_profile.html
├── static/
│   ├── css/theme.css
│   └── js/app.js
├── requirements.txt
├── .env.example
└── manage.py
```

## Run locally

```bash
cd healthcare
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit .env if you want to change defaults

python manage.py migrate
python manage.py seed_demo_data  # creates a demo doctor + patient + sample readings
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

### Demo login credentials (created by `seed_demo_data`)

| Role    | Phone        | Password   |
|---------|--------------|------------|
| Doctor  | 9999999999   | demo1234   |
| Patient | 8888888888   | (none — patient login has no password) |

## Configuring the API URL

The frontend and API live in the same Django app, so by default everything calls the
same origin (`/api/...`) — nothing to configure for local use.

If you ever split the frontend off (e.g. host it separately from the Django API), set
`window.API_BASE_URL` at the top of `static/js/app.js`, or inject it via the template,
e.g.:

```html
<script>window.API_BASE_URL = "https://your-api-host.com";</script>
```

Every fetch in the templates goes through the `ccApi(path)` helper in `app.js`, so
changing that one value repoints the whole frontend.

## Where your ESP32 / Django REST API connects

Your ESP32 (or any client) POSTs sensor readings to:

```
POST /api/data/
Content-Type: application/json

{
  "patient_id": 1,
  "temperature": 36.7,
  "humidity": 58.0,
  "ax": 0.021,
  "ay": -0.034,
  "az": 0.982,
  "emergency": false,
  "device_id": "ESP32-01"      // optional
}
```

The buzzer (GPIO 27) and emergency button (GPIO 26) are handled on the ESP32 side —
when the button is pressed, have the firmware send `"emergency": true` in this same
payload. The website will immediately show the red emergency banner and log an alert.

Full API reference:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/data/` | ESP32 sensor ingest |
| GET | `/api/patient/<id>/?limit=30` | Temperature history for the chart |
| GET | `/api/patient/<id>/latest/` | Live poll: latest reading + device + patient info |
| GET | `/api/patient/<id>/profile/` | Full patient profile |
| GET | `/api/patient/<id>/device/` | Device connection status |
| POST | `/api/add-patient/` | Add a patient |
| GET | `/api/doctor-patients/<id>/` | Doctor's patient list |
| GET | `/api/doctor-overview/<id>/` | Dashboard summary cards |
| GET | `/api/alerts/<id>/` | Alert history (filterable by `type`, `date`, `patient_id`) |
| POST | `/api/alerts/acknowledge/<alert_id>/` | Acknowledge an alert |
| GET | `/api/reports/<id>/` | Report stats + chart data (filterable by `patient_id`, `from`, `to`) |

## Demo Mode vs. Live API Mode (in the UI)

The patient monitoring page has a **LIVE API MODE / DEMO MODE** pill in its top bar. In
demo mode, the page generates realistic sample readings client-side (temperature mostly
36.2–37.4°C with occasional 38.2–38.8°C spikes) — useful when the backend or ESP32 isn't
reachable yet. This is separate from `seed_demo_data`, which seeds real database rows for
testing the actual API.

## Deploying to the cloud

1. Set real environment variables (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`,
   `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`) on your host — never commit
   `.env`.
2. Run `python manage.py collectstatic` and serve `staticfiles/` (e.g. with WhiteNoise,
   or your host's static file handling) since `DEBUG=False` disables Django's built-in
   static serving.
3. Point `DATABASES` at a production database if you're not staying on SQLite (SQLite is
   fine for a prototype/demo deployment such as PythonAnywhere).
4. Any static host (PythonAnywhere, Railway, Render, etc.) works since this is a normal
   Django app — no separate frontend build step is needed.

## Notes

- This is a student engineering prototype. Wording throughout says "high temperature
  detected", never a medical diagnosis like "fever".
- Humidity is stored on every reading but intentionally not shown as a health card on
  the monitoring page, per the spec — it's available in the database for future use.
- `@csrf_exempt` remains on `login_user` and DRF's `@api_view` endpoints accept
  unauthenticated POSTs so the ESP32 can post without a login flow. For anything beyond
  a prototype, add token authentication to the ingest endpoint.
