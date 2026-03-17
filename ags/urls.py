from django.urls import path
from . import views

urlpatterns = [
    path('', views.LandingView.as_view(), name='landing'),
    path('propose/', views.ProposeAGView.as_view(), name='propose_ag'),
    path('register/', views.RegisterSchuelerStep1View.as_view(), name='register_schueler'),
    path('register/select/', views.select_ags, name='select_ags'),
    path('login/', views.RequestMagicLinkView.as_view(), name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('stats/', views.stats_dashboard, name='stats_dashboard'),
    path('stats/export/', views.stats_export, name='stats_export'),
    path('stats/export-csv/', views.export_ags_csv, name='export_ags_csv'),
    path('manual-intervention/', views.manual_intervention, name='manual_intervention'),
    path('resend-email/', views.resend_email, name='resend_email'),
    path('resend-leader-email/', views.resend_leader_email, name='resend_leader_email'),
    path('run-lottery-internal/', views.run_lottery_view, name='run_lottery_internal'),
    path('test-email/', views.test_email, name='test_email'),
    path('impressum/', views.impressum, name='impressum'),
]
