from django.shortcuts import render, redirect, get_object_or_404
from .models import Asset, Reservation, Maintenance, AuditLog   # <-- ADDED
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required

import csv                    # <-- ADDED
from django.http import HttpResponse   # <-- ADDED
from reportlab.pdfgen import canvas     # <-- ADDED


@login_required
def dashboard(request):
    total_assets = Asset.objects.count()
    available_assets = Asset.objects.filter(status="available").count()
    unavailable_assets = Asset.objects.exclude(status="available").count()

    recent_assets = Asset.objects.order_by('-created_at')[:5]
    recent_maintenances = Maintenance.objects.select_related("asset").order_by('-start_date')[:5]

    return render(request, "dashboard.html", {
        "total_assets": total_assets,
        "available_assets": available_assets,
        "unavailable_assets": unavailable_assets,
        "recent_assets": recent_assets,
        "recent_maintenances": recent_maintenances,
    })


def asset_list(request):
    assets = Asset.objects.all().order_by('name')
    return render(request, "assets/asset_list.html", {"assets": assets})


def add_asset(request):
    if request.method == "POST":
        name = request.POST.get("name")
        serial = request.POST.get("serial_number")
        category = request.POST.get("category")
        location = request.POST.get("location")
        image = request.FILES.get("image")

        if Asset.objects.filter(serial_number=serial).exists():
            messages.error(request, "Asset with this serial number already exists.")
            return redirect("add_asset")

        asset = Asset.objects.create(
            name=name,
            serial_number=serial,
            category=category or "",
            location=location or "",
            image=image
        )

        # ADD AUDIT LOG
        AuditLog.objects.create(
            asset=asset,
            action="created",
            description=f"Asset '{asset.name}' created",
            user=request.user
        )

        messages.success(request, "Asset created.")
        return redirect("asset_list")

    return render(request, "assets/add_asset.html")


def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    return render(request, "assets/asset_detail.html", {"asset": asset})


def edit_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    if request.method == "POST":
        asset.name = request.POST.get("name") or asset.name
        asset.serial_number = request.POST.get("serial_number") or asset.serial_number
        asset.category = request.POST.get("category") or asset.category
        asset.location = request.POST.get("location") or asset.location
        asset.status = request.POST.get("status") or asset.status

        new_image = request.FILES.get("image")
        if new_image:
            asset.image = new_image

        try:
            asset.save()

            # ADD AUDIT LOG
            AuditLog.objects.create(
                asset=asset,
                action="updated",
                description=f"Asset '{asset.name}' updated",
                user=request.user
            )

            messages.success(request, "Asset updated.")
        except Exception as e:
            messages.error(request, f"Error updating asset: {e}")

        return redirect("asset_detail", pk=asset.pk)

    return render(request, "assets/edit_asset.html", {"asset": asset})


def delete_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == "POST":

        # ADD AUDIT LOG
        AuditLog.objects.create(
            asset=asset,
            action="status_changed",
            description=f"Asset '{asset.name}' deleted",
            user=request.user
        )

        asset.delete()
        messages.success(request, "Asset deleted.")
        return redirect("asset_list")

    return render(request, "assets/delete_confirm.html", {"asset": asset})


def reservation_list(request):
    reservations = Reservation.objects.select_related("asset").order_by("-check_in")
    return render(request, "assets/reservation_list.html", {"reservations": reservations})


def add_reservation(request):
    assets = Asset.objects.filter(status="available").order_by('name')

    if request.method == "POST":
        asset_id = request.POST.get("asset")
        username = request.POST.get("user_name")
        checkin_str = request.POST.get("checkin_date")
        days = int(request.POST.get("days", "1"))

        asset = get_object_or_404(Asset, id=asset_id)

        try:
            if 'T' in checkin_str:
                checkin = datetime.fromisoformat(checkin_str)
            else:
                checkin = datetime.fromisoformat(checkin_str + "T00:00:00")
        except Exception:
            messages.error(request, "Invalid date format.")
            return redirect("add_reservation")

        checkout = checkin + timedelta(days=days)

        Reservation.objects.create(
            asset=asset,
            user_name=username,
            check_in=checkin,
            check_out=checkout,
            days=days,
            status="booked",
        )

        asset.status = "unavailable"
        asset.save()

        # AUDIT LOG
        AuditLog.objects.create(
            asset=asset,
            action="checked_out",
            description=f"Asset '{asset.name}' reserved for {username}",
            user=request.user
        )

        messages.success(request, "Reservation created.")
        return redirect("reservation_list")

    return render(request, "assets/add_reservation.html", {"assets": assets})


def checkout_reservation(request, pk):
    reservation = get_object_or_404(Reservation, id=pk)

    reservation.checkout_asset()

    # AUDIT LOG
    AuditLog.objects.create(
        asset=reservation.asset,
        action="returned",
        description=f"Asset '{reservation.asset.name}' returned",
        user=request.user
    )

    messages.success(request, "Asset checked out successfully and is now available again.")
    return redirect("reservation_list")


@login_required
def add_maintenance(request):
    assets = Asset.objects.exclude(status="maintenance").order_by("name")
    
    if request.method == "POST":
        asset_id = request.POST.get("asset")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        hours = request.POST.get("hours")
        cost = request.POST.get("cost")
        notes = request.POST.get("notes")
        
        asset = get_object_or_404(Asset, id=asset_id)
        
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except Exception:
            messages.error(request, "Invalid date format.")
            return redirect("add_maintenance")
        
        maintenance = Maintenance.objects.create(
            asset=asset,
            start_date=start_dt,
            end_date=end_dt,
            hours=hours or None,
            cost=cost or None,
            notes=notes or "",
            status="in_progress"
        )

        # AUDIT LOG
        AuditLog.objects.create(
            asset=asset,
            action="maintenance_created",
            description=f"Maintenance started for '{asset.name}'",
            user=request.user
        )

        messages.success(request, "Maintenance scheduled.")
        return redirect("maintenance_list")
    
    return render(request, "assets/add_maintenance.html", {"assets": assets})


@login_required
def maintenance_list(request):
    maintenances = Maintenance.objects.select_related("asset").order_by("-start_date")
    return render(request, "assets/maintenance_list.html", {"maintenances": maintenances})


@login_required
def complete_maintenance(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)
    maintenance.status = "done"
    maintenance.save()

    # AUDIT LOG
    AuditLog.objects.create(
        asset=maintenance.asset,
        action="maintenance_completed",
        description=f"Maintenance completed for '{maintenance.asset.name}'",
        user=request.user
    )

    messages.success(request, f"{maintenance.asset.name} maintenance completed.")
    return redirect("maintenance_list")



# -------------------------------
#    AUDIT LOG LIST VIEW
# -------------------------------
@login_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related("asset").order_by("-timestamp")
    return render(request, "auditlog_list.html", {"logs": logs})


# -------------------------------
#    EXPORT CSV
# -------------------------------
@login_required
def export_audit_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=\"audit_log.csv\"'

    writer = csv.writer(response)
    writer.writerow(["Asset", "Action", "Description", "User", "Timestamp"])

    for log in AuditLog.objects.all().order_by("-timestamp"):
        writer.writerow([
            log.asset.name if log.asset else "",
            log.get_action_display(),
            log.description,
            log.user,
            log.timestamp,
        ])
    return response


# -------------------------------
#    EXPORT PDF CHECKPOINT
# -------------------------------
@login_required
def export_audit_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=\"audit_checkpoint.pdf\"'

    p = canvas.Canvas(response)
    y = 800

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Asset Verification Checkpoint Report")
    y -= 40

    p.setFont("Helvetica", 12)

    for log in AuditLog.objects.all().order_by('-timestamp'):
        p.drawString(
            50, y,
            f"- {log.timestamp.strftime('%d %b %Y %H:%M')} | {log.asset} | {log.get_action_display()} | {log.description}"
        )
        y -= 20

        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 800

    p.showPage()
    p.save()
    return response
