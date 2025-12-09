from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
import requests
from . import mail
from .models import Application, Scholarship, StudentProfile
import datetime
from dateutil.relativedelta import relativedelta
from flask_mail import Message
from .utils import student_required, check_not_applied


student = Blueprint('student', __name__)
    
def find_eligible_requirements(scholarship_id, user_id):

    scholarship_requirements = Scholarship.query.filter_by(id=scholarship_id).first().requirements
    user_profile = StudentProfile.query.filter_by(user_id=user_id).first().results

    scholarship_requirements = {key: value for key, value in scholarship_requirements.items() if value is not None}
    user_profile = {key: value for key, value in user_profile.items() if value is not None}

    matched_requirements = []

    for key, value in scholarship_requirements.items():
        if key == "gpa" and user_profile.get(key, 0) >= value:
            matched_requirements.append(key.upper())
        elif key in ["major", "minor"]:
            profile_value = user_profile.get(key)

            if profile_value in value:
                matched_requirements.append(key.upper())

        elif key not in ["gpa", "major", "minor"] and user_profile.get(key) == value:
            matched_requirements.append(key.upper())
    return matched_requirements

@student.route('/scholarship-directory')
@login_required
@student_required
def scholarship_directory():

    scholarships = Scholarship.query.all()

    return render_template("student/scholarship-directory.html", user=current_user, scholarships=scholarships)

@student.route('/scholarship-directory/<criteria>/<criteria_value>')
@login_required
@student_required
def filtered_scholarships(criteria,criteria_value):

    query = Scholarship.query

    if criteria == "Major":
        query = query.filter(Scholarship.eligible_majors.like(f'%"{criteria_value}"%'))
    if criteria == "Minor":
        query = query.filter(Scholarship.eligible_minors.like(f'%"{criteria_value}"%'))
    if criteria == "Donor":
        query = query.filter(Scholarship.donor_name == criteria_value)
    if criteria == "GPA":
        gpa_min = criteria_value.split(" ")[0]
        gpa_max = criteria_value.split(" ")[2]
        query = query.filter(Scholarship.required_gpa >= gpa_min, Scholarship.required_gpa <= gpa_max)
    if criteria == "Deadline":
        deadline_start = datetime.datetime.strptime(criteria_value, 'Deadline In %B %Y')
        deadline_end = deadline_start + relativedelta(months=1)
        query = query.filter(Scholarship.application_deadline >= deadline_start, Scholarship.application_deadline < deadline_end)
    if criteria == "Amount":
        amount_min = criteria_value.split(" ")[0]
        amount_max = criteria_value.split(" ")[2]

        if(amount_min != "Greater"):
            query = query.filter(Scholarship.amount >= amount_min, Scholarship.amount <= amount_max)
        else:
            query = query.filter(Scholarship.amount >= amount_max)

    if criteria == "Available":
        available_min = criteria_value.split(" ")[0]
        available_max = criteria_value.split(" ")[2]

        if(available_min != "Greater"):
            query = query.filter(Scholarship.scholarships_available >= available_min, Scholarship.scholarships_available <= available_max)
        else:
            query = query.filter(Scholarship.scholarships_available >= available_max)

    scholarships = query.all()

    return render_template("student/scholarship-list.html", user=current_user, scholarships=scholarships, criteria={"type":criteria,"value":criteria_value})

@student.route('/applications')
@login_required
@student_required
def applications():

    applications = Application.query.filter_by(user_id = current_user.id).all()

    return render_template("student/student-applications.html", user=current_user, applications=applications)


@student.route('/scholarship-directory/<int:id>')
@login_required
@student_required
def scholarship_detail(id):

    scholarship = Scholarship.query.filter_by(id = id).first()
    eligible_reqs = find_eligible_requirements(id, current_user.id)
    already_applied = Application.query.filter_by(scholarship_id = id, user_id = current_user.id).first()

    return render_template("student/scholarship-detail.html", user=current_user, scholarship=scholarship, eligible_reqs = eligible_reqs, already_applied = already_applied)

@student.route('/scholarship-directory/<int:id>/apply',methods=["GET","POST"])
@login_required
@student_required
@check_not_applied
def scholarship_apply(id):

    scholarship = Scholarship.query.filter_by(id = id).first()
    eligible_reqs = find_eligible_requirements(id, current_user.id)

    if request.method == "POST":
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

            "scholarship_id": id,
            "user_id": current_user.id,    
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
            
        app_response = requests.post("http://localhost:5000/api/applications", json=form_data, cookies=request.cookies)
        
        application_id = app_response.json().get("id")

        uploaded_file = request.files.get("document")
        document_type = request.form.get("document_type")

        if uploaded_file and uploaded_file.filename:
            files = {"document": (uploaded_file.filename, uploaded_file, uploaded_file.mimetype)}
            data = {"application_id": application_id, "document_type": document_type}

            requests.post("http://localhost:5000/api/documents", files=files, data=data, cookies=request.cookies)

        flash("Your scholarship application has been successfully submitted",category="success")
        msg = Message("SAS - New Application Submitted", recipients=[scholarship.donor_email])
        msg.body = f"Student {current_user.first_name} {current_user.last_name} has applied for the scholarship '{scholarship.name}'"
        mail.send(msg)
        return redirect(url_for('student.applications'))

    return render_template("student/scholarship-apply.html", user=current_user, scholarship=scholarship, eligible_reqs = eligible_reqs)