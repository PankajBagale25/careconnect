from django.urls import path
from .views import *

urlpatterns = [
    # LOGIN
    path('', login_page, name='login_page'),
    path('login/', login_user, name='login_user'),
    path('logout/', logout_user, name='logout'),

    # PAGES
    path('dashboard/', dashboard, name='dashboard'),
    path('doctor/', doctor_dashboard, name='doctor_dashboard'),
    path('alerts/', alerts_page, name='alerts_page'),
    path('reports/', reports_page, name='reports_page'),
    path('patient-profile/', patient_profile_page, name='patient_profile_page'),
    path('settings/', settings_page, name='settings_page'),

    # API - INGEST
    path('api/data/', save_data, name='save_data'),

    # API - PATIENT
    path('api/patient/<int:patient_id>/', patient_data, name='patient_data'),
    path('api/patient/<int:patient_id>/latest/', patient_latest, name='patient_latest'),
    path('api/patient/<int:patient_id>/profile/', patient_profile_data, name='patient_profile_data'),
    path('api/patient/<int:patient_id>/device/', device_status_api, name='device_status_api'),

    # API - DOCTOR
    path('api/add-patient/', add_patient, name='add_patient'),
    path('api/doctor-patients/<int:doctor_id>/', doctor_patients, name='doctor_patients'),
    path('api/doctor-overview/<int:doctor_id>/', doctor_overview, name='doctor_overview'),
    path('api/reports/<int:doctor_id>/', reports_data, name='reports_data'),

    # API - ALERTS
    path('api/alerts/<int:doctor_id>/', alerts_list, name='alerts_list'),
    path('api/alerts/acknowledge/<int:alert_id>/', acknowledge_alert, name='acknowledge_alert'),
]
