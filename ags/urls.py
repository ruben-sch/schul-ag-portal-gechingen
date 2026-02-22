from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('propose/', views.propose_ag, name='propose_ag'),
    path('register/', views.register_schueler, name='register_schueler'),
    path('register/select/', views.select_ags, name='select_ags'),
    path('login/', views.request_magic_link, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stats/', views.stats_dashboard, name='stats_dashboard'),
    path('stats/export/', views.stats_export, name='stats_export'),
    path('manual-intervention/', views.manual_intervention, name='manual_intervention'),
    path('run-lottery-internal/', views.run_lottery_view, name='run_lottery_internal'),
    path('test-email/', views.test_email, name='test_email'),
    path('impressum/', views.impressum, name='impressum'),
]
