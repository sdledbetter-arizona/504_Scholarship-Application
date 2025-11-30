from flask import Blueprint, flash, redirect, render_template, request, url_for, abort
from flask_login import login_required, current_user
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from .models import StudentProfile, User, SecurityQuestion, TicketRequest, Scholarship,Application, AuditLog, Notification
from . import db
from .utils import apply_changes_with_audit


views = Blueprint('views', __name__)

@views.route('/')
@login_required
def home():
    if current_user.user_type == 'Scholarship Donor':

        scholarships_data = Scholarship.query.filter_by(donor_id = current_user.id).all()
        applications_data = Application.query.all()

        for scholarship in scholarships_data:
            scholarship.applications = [app for app in applications_data if app.scholarship_id == scholarship.id]


        scholarship_ids = db.session.query(Scholarship.id).filter(Scholarship.donor_id == current_user.id).subquery()

        applications_data = Application.query.filter(Application.scholarship_id.in_(scholarship_ids.select())).all()

        return render_template("donor/donor-overview.html", user=current_user, total_scholarships = len(scholarships_data), total_applications = len(applications_data))
    elif current_user.user_type == 'Application Reviewer':
        return render_template("reviewer/reviewer-overview.html", user=current_user)
    elif current_user.user_type == 'Scholarship Admin':
        total_users = User.query.count()
        open_requests = TicketRequest.query.filter_by(status="Open").count()
        total_scholarships = Scholarship.query.count()
        total_applications = Application.query.count()

        recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

        return render_template("admin/admin-overview.html", user=current_user, total_users=total_users, 
                                open_requests=open_requests, total_scholarships=total_scholarships,
                                total_applications=total_applications,
                                recent_logs=recent_logs)
    else:

        pending_count = (Application.query.filter_by(user_id=current_user.id, status="Pending Decision").count())

        return render_template("student/student-overview.html", user=current_user, pending_count = pending_count)


@views.route('/about')
def need_help():
    return render_template("views/need-help.html", user=current_user)


@views.route("/notifications")
@login_required
def notifications_page():
    notes = Notification.query.filter_by(
    user_id=current_user.id,
    is_read=False).order_by(Notification.created_at.desc()).all()
    return render_template("views/notifications.html", user=current_user, notifications=notes)

@views.post("/notifications/read/<int:id>")
@login_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)

    if notification.user_id != current_user.id:
        abort(403)

    apply_changes_with_audit(
        entity=notification,
        data={"is_read": True},         
        field_map={"is_read": "is_read"},
        user_id=current_user.id,
        action="Notification Read",
        per_field=True
    )

    db.session.commit()
    return redirect(url_for("views.notifications_page"))

@views.post("/notifications/read-all")
@login_required
def mark_all_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id)

    for notification in notifications:
        apply_changes_with_audit(
            entity=notification,
            data={"is_read": True},         
            field_map={"is_read": "is_read"},
            user_id=current_user.id,
            action="Notification Read",
            per_field=True
        )

    db.session.commit()
    return redirect(url_for("views.notifications_page"))

@views.route('/profile',methods=["GET","POST"])
@login_required
def profile():

    sec_quests = SecurityQuestion.query.all()
    user_profile = StudentProfile.query.filter_by(user_id = current_user.id).first()

    if(request.method == 'POST'):
        profile_form_name = request.form.get('ProfileFormName')
        api_request_url = "http://localhost:5000/api/requests"

        if(profile_form_name == 'DeleteAccount'):

            password = request.form.get('del-acct-pwd')

            if not (check_password_hash(current_user.password, password)):
                flash("Invalid Password.", category="danger")

            else:

                form_data = {
                    "user_id":current_user.id,
                    "request_type":"Delete Account",
                    "details":{
                        "username": current_user.username,
                        "email": current_user.email,
                        "first_name": current_user.first_name,
                        "last_name": current_user.last_name,
                        "net_id": current_user.net_id if current_user.net_id else None,
                        "phone_num": current_user.phone_num
                    }
                }
                
                requests.post(api_request_url, json=form_data)

                form_data = {
                    "status": "Disabled"
                }
                
                api_url = f"http://localhost:5000/api/users/{current_user.id}"
                requests.put(api_url, json=form_data)

                flash("You account has been prepped for deletion. Hope to see you again!",category="warning")
                return redirect(url_for('auth.logout'))

        elif(profile_form_name == 'ChangePassword'):
            cur_pwd = request.form.get('currentPassword')
            new_pwd = request.form.get('newPassword')
            new_pwd_conf = request.form.get('newPasswordConf')

            if not (check_password_hash(current_user.password, cur_pwd)):
                flash("Invalid Current Password.", category="danger")

            if new_pwd != new_pwd_conf:
                flash("New Passwords do not match.", category="danger")
            
            else:
                user = User.query.filter_by(id = current_user.id).first()
                user.password = generate_password_hash(new_pwd, method='pbkdf2:sha256')
                db.session.commit()
                flash("Your password has been successfully reset.", category='success')

        elif(profile_form_name == 'SecurityQuestions'):
            flash("CHANGE SEC QUESTIONS",category="warning")

        elif(profile_form_name == 'ChangeRole'):
            requested_role = request.form.get('options')
            form_data = {
                    "user_id":current_user.id,
                    "request_type":"Change Role",
                    "details":{
                        "user_type": requested_role
                    }
                }
                
            requests.post(api_request_url, json=form_data)
            flash("Your change role request has been sucessfully submitted.", category="success")
            
        else:
            
            preferred_pronoun = request.form.get('preferred_pronoun')
            student_id = request.form.get('student_id')
            major = request.form.get('major')
            minor = request.form.get('minor')
            cumulative_gpa = request.form.get('cumulative_gpa')
            current_year = request.form.get('current_year')
            ethnicity = request.form.get('ethnicity')
            personal_statement_essay = request.form.get('personal_statement_essay')
            work_experience = request.form.get('work_experience')

            form_data = {
                    "user_id":current_user.id,
                    "request_type":"Edit Profile",
                    "details":{
                        "preferred_pronoun": preferred_pronoun,
                        "student_id": student_id,
                        "major": major,
                        "minor": minor,
                        "cumulative_gpa": cumulative_gpa,
                        "current_year": current_year,
                        "ethnicity": ethnicity,
                        "personal_statement_essay": personal_statement_essay,
                        "work_experience": work_experience
                    }
                }
                
            requests.post(api_request_url, json=form_data)
            flash("Your edit profile request has been successfully submitted ",category="success")

    return render_template("views/profile.html", user=current_user, sec_quests = sec_quests, profile = user_profile)