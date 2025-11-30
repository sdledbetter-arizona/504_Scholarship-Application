from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from .utils import logout_required
from .models import User, SecurityQuestion, Scholarship, Application
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
import datetime
from zoneinfo import ZoneInfo
import requests
from .utils import donor_required


donor = Blueprint('donor', __name__)

@donor.route('/scholarships', methods=['GET','POST'])
@login_required
@donor_required
def scholarships():

    
    api_request_url = "http://localhost:5000/api/requests"

    scholarships_data = Scholarship.query.filter_by(donor_id = current_user.id).all()
    applications_data = Application.query.all()

    
    for scholarship in scholarships_data:
        scholarship.applications = [app for app in applications_data if app.scholarship_id == scholarship.id]

    if(request.method == 'POST'):
        name = request.form.get('name')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        donor_name = request.form.get('donor_name')
        donor_phone = request.form.get('donor_phone')
        donor_email = request.form.get('donor_email')
        scholarships_available = request.form.get('scholarships_available')
        eligible_majors = request.form.get('eligible_majors')
        eligible_minors = request.form.get('eligible_minors')
        required_gpa = float(request.form.get('required_gpa')) if request.form.get('required_gpa') else None
        application_deadline = datetime.datetime.strptime(request.form.get('application_deadline'), "%Y-%m-%d").date().isoformat()
        other_requirements = request.form.get('other_requirements')

        form_data = {
                "user_id":current_user.id,
                "request_type":"Create Scholarship",
                "details":{
                    "name": name,
                    "description":description,
                    "amount": amount,
                    "donor_name": donor_name,
                    "donor_phone": donor_phone,
                    "donor_email": donor_email,
                    "scholarships_available": scholarships_available,
                    "eligible_majors": eligible_majors,
                    "eligible_minors": eligible_minors,
                    "required_gpa": required_gpa,
                    "application_deadline": application_deadline,
                    "other_requirements": other_requirements
                }
            }
            
        requests.post(api_request_url, json=form_data)
        flash("Your create scholarship request has been successfully submitted ",category="success")

    return render_template("donor/donor-scholarships.html", user=current_user, scholarships = scholarships_data)

@donor.route('/applications', methods=['GET','POST'])
@login_required
@donor_required
def applications():

    
    api_request_url = "http://localhost:5000/api/requests"

    scholarship_ids = db.session.query(Scholarship.id).filter(Scholarship.donor_id == current_user.id).subquery()

    applications_data = Application.query.filter(
        Application.scholarship_id.in_(
            scholarship_ids.select() 
        )
    ).all()

    if(request.method == 'POST'):
        name = request.form.get('name')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        scholarships_available = request.form.get('scholarships_available')
        eligible_majors = request.form.get('eligible_majors')
        eligible_minors = request.form.get('eligible_minors')
        required_gpa = float(request.form.get('required_gpa')) if request.form.get('required_gpa') else None
        application_deadline = datetime.datetime.strptime(request.form.get('application_deadline'), "%Y-%m-%d").date().isoformat()
        other_requirements = request.form.get('other_requirements')

        form_data = {
                "user_id":current_user.id,
                "request_type":"Create Scholarship",
                "details":{
                    "name": name,
                    "description":description,
                    "amount": amount,
                    "donor_name": current_user.full_name,
                    "donor_phone": current_user.phone_num,
                    "donor_email": current_user.email,
                    "scholarships_available": scholarships_available,
                    "eligible_majors": eligible_majors,
                    "eligible_minors": eligible_minors,
                    "required_gpa": required_gpa,
                    "application_deadline": application_deadline,
                    "other_requirements": other_requirements
                }
            }
            
        requests.post(api_request_url, json=form_data)
        flash("Your create scholarship request has been successfully submitted ",category="success")


    return render_template("donor/donor-applications.html", user=current_user, applications = applications_data)