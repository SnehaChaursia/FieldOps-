from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import (
    audit_log_list,
    export_audit_csv,
    export_audit_pdf
)


urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),

    path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    path("", views.asset_list, name="asset_list"),
    path("add/", views.add_asset, name="add_asset"),
    path("<int:pk>/", views.asset_detail, name="asset_detail"),
    path("<int:pk>/edit/", views.edit_asset, name="edit_asset"),
    path("<int:pk>/delete/", views.delete_asset, name="delete_asset"),

    path("reservation/", views.reservation_list, name="reservation_list"),
    path("reservation/add/", views.add_reservation, name="add_reservation"),
    path("reservation/<int:pk>/checkout/", views.checkout_reservation, name="checkout_reservation"),

    path("maintenance/", views.maintenance_list, name="maintenance_list"),
    path("maintenance/add/", views.add_maintenance, name="add_maintenance"),
    path("maintenance/<int:pk>/complete/", views.complete_maintenance, name="complete_maintenance"),


    path("audit/logs/", audit_log_list, name="audit_log_list"),
    path("audit/logs/csv/", export_audit_csv, name="export_audit_csv"),
    path("audit/logs/pdf/", export_audit_pdf, name="export_audit_pdf"),
]


