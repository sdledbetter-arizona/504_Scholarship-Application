from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from .models import Application, Scholarship, TicketRequest, User, StudentProfile, AuditLog
from . import db
from .utils import admin_required
from sqlalchemy import func

admin = Blueprint('admin', __name__)

@admin.route('/scholarships')
@login_required
@admin_required
def scholarships():

    scholarships_data = Scholarship.query.all()
    applications_data = Application.query.all()
    
    for scholarship in scholarships_data:
        scholarship.applications = [app for app in applications_data if app.scholarship_id == scholarship.id]

    return render_template("admin/admin-scholarships.html", user=current_user, scholarships = scholarships_data)

@admin.route('/scholarships/<int:id>',methods=["GET"])
@login_required
@admin_required
def scholarship_detail(id):

    scholarship = []

    if(not scholarship):
        abort(404)

    return render_template("admin/admin-scholarship-detail.html", scholarship=scholarship, user=current_user)


@admin.route('/applications')
@login_required
@admin_required
def applications():

    applications_data = Application.query.all()

    return render_template("admin/admin-applications.html", applications=applications_data, user=current_user)

@admin.route('/applications/<int:id>',methods=["GET"])
@login_required
@admin_required
def application_detail(id):

    application = []

    if(not application):
        abort(404)

    return render_template("admin/admin-application-detail.html", application=application, user=current_user)


@admin.route('/requests')
@login_required
@admin_required
def requests():

    open_requests = TicketRequest.query.filter(TicketRequest.status.like("Open")).all()
    closed_requests = TicketRequest.query.filter(TicketRequest.status.like("Closed - %")).all()

    return render_template("admin/admin-requests.html", open_requests = open_requests, closed_requests = closed_requests, user=current_user)

@admin.route('/requests/<int:id>',methods=["GET"])
@login_required
@admin_required
def request_detail(id):

    request = TicketRequest.query.filter_by(id = id).first()

    user_detail = User.query.filter_by(id = request.user_id).first()

    if(not request):
        abort(404)

    request.details.pop("security_questions", None)
    request.details.pop("password", None)

    return render_template("admin/admin-request-detail.html", request=request,user_detail = user_detail, user=current_user)

@admin.route('/users')
@login_required
@admin_required
def users():

    users = User.query.all()

    return render_template("admin/admin-users.html", users = users, user=current_user)

@admin.route('/users/<int:id>',methods=["GET"])
@login_required
@admin_required
def user_detail(id):

    user = User.query.filter_by(id = id).first()
    student_profile = StudentProfile.query.filter_by(user_id = id).first()

    if(not user):
        abort(404)

    return render_template("admin/admin-user-detail.html", user_detail=user, user=current_user, student_profile = student_profile)


@admin.route("/audit-logs")
@login_required
@admin_required
def audit_logs():
    # Most recent first
    logs = (AuditLog.query.order_by(AuditLog.created_at.desc()).all())
    return render_template("admin/admin-audit-logs.html", user=current_user, logs=logs)