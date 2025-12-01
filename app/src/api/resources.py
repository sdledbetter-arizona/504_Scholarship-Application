import datetime
from zoneinfo import ZoneInfo
from flask import request, jsonify
from flask_login import current_user
from flask_restful import Resource
import requests, json
from werkzeug.utils import secure_filename
from src.models import *
from .. import mail
from flask_mail import Message
from src.utils import calculate_matching_score
from src.utils import apply_changes_with_audit, log_change


def serialize_entity(entity):
    """Serialize a SQLAlchemy model to a dict for logging."""
    return {c.name: getattr(entity, c.name) for c in entity.__table__.columns}


def current_user_id_or_none():
    return getattr(current_user, "id", None)


class TicketRequestResource(Resource):

    def get(self, request_id=None):
        if request_id:
            ticket = TicketRequest.query.get(request_id)
            if not ticket:
                return {"message": "Ticket not found"}, 404
            return {
                "id": ticket.id,
                "user_id": ticket.user_id,
                "request_type": ticket.request_type,
                "details": ticket.details,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat(),
                "approval_status": ticket.approval_status,
                "approved_by": ticket.approved_by,
                "approved_at": ticket.approved_at.isoformat() if ticket.approved_at else None
            }, 200
        else:
            tickets = TicketRequest.query.all()
            return [{
                "id": t.id,
                "user_id": t.user_id,
                "request_type": t.request_type,
                "details": t.details,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "approval_status": t.approval_status,
                "approved_by": t.approved_by,
                "approved_at": t.approved_at.isoformat() if t.approved_at else None
            } for t in tickets], 200

    def post(self):
        data = request.get_json()

        new_ticket = TicketRequest(
            user_id=data["user_id"],
            request_type=data["request_type"],
            details=data.get("details"))
        db.session.add(new_ticket)
        db.session.flush()  # ensure new_ticket.id exists for audit log

        field_map = {
            "user_id": "user_id",
            "request_type": "request_type",
            "details": "details",
            "created_at": "created_at",
            "approval_status":"approval_status"
        }

        for _, model_attr in field_map.items():
            new_val = getattr(new_ticket, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created Ticket Request",
                entity=new_ticket,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )


        db.session.commit()

        all_admins = User.query.filter_by(user_type="Scholarship Admin").all()

        for admin in all_admins:
            api_url = "http://localhost:5000/api/notifications"
            requests.post(
                api_url,
                json={
                    "user_id": admin.id,
                    "title": "New Request Submitted",
                    "message": f"Request '{new_ticket.request_type}' has been created.",
                    "url": f"/admin/requests/{new_ticket.id}",
                },
            )

            msg = Message("SAS - Notification", recipients=[admin.email])
            msg.body = "A new request has been submitted."
            mail.send(msg)

        return {"message": "Ticket request created", "id": new_ticket.id}, 201

    def put(self, request_id, approval_status=None):
        ticket = TicketRequest.query.get(request_id)
        if not ticket:
            return {"message": "Ticket request not found"}, 404

        if not approval_status or approval_status not in ["approve", "reject", "cancel"]:
            return {"message": "Invalid approval status"}, 400

        if ticket.status != "Open":
            return {"message": "Ticekt request is already closed"}, 400

        # Convenience: keep old values for audit of status changes
        def audit_ticket_status_change(action_label: str):
            """Log key status/approval fields as a grouped action."""
            log_change(
                user_id=current_user_id_or_none(),
                action=action_label,
                entity=ticket,
                field_name="status",
                old_value=ticket.status,
                new_value=ticket.status,
            )

        if approval_status == "reject":

            if ticket.request_type == "Delete Account":
                form_data = {
                    "status": "Enabled"
                }
                api_url = f"http://localhost:5000/api/users/{ticket.user_id}"
                requests.put(api_url, json=form_data, cookies=request.cookies)

            old_status = ticket.status
            old_approval_status = ticket.approval_status

            ticket.approval_status = "Rejected"
            ticket.approved_by = current_user.id
            ticket.approved_at = datetime.datetime.now(ZoneInfo("America/Phoenix"))
            ticket.status = "Closed - Rejected"

            # Audit the change in status & approval_status
            log_change(
                user_id=current_user_id_or_none(),
                action="Rejected Ticket Request",
                entity=ticket,
                field_name="status",
                old_value=old_status,
                new_value=ticket.status,
            )
            log_change(
                user_id=current_user_id_or_none(),
                action="Rejected Ticket Request",
                entity=ticket,
                field_name="approval_status",
                old_value=old_approval_status,
                new_value=ticket.approval_status,
            )

            db.session.commit()

            if ticket.request_type == "Create Account":
                msg = Message("SAS - Request Rejected", recipients=[ticket.details["email"]])
                msg.body = f"Your request for {ticket.request_type} has been rejected by an Administrator."
                mail.send(msg)
            else:
                msg = Message(
                    "SAS - Request Rejected",
                    recipients=[User.query.filter_by(id=ticket.user_id).first().email],
                )
                msg.body = f"Your request for {ticket.request_type} has been rejected by an Administrator."
                mail.send(msg)
            return {"message": "Ticket request has been rejected"}, 200

        elif approval_status == "cancel":
            old_status = ticket.status
            old_approval_status = ticket.approval_status

            ticket.approval_status = "Cancelled"
            ticket.status = "Closed - Cancelled"

            log_change(
                user_id=current_user_id_or_none(),
                action="Cancelled Ticket Request",
                entity=ticket,
                field_name="status",
                old_value=old_status,
                new_value=ticket.status,
            )
            log_change(
                user_id=current_user_id_or_none(),
                action="Cancelled Ticket Request",
                entity=ticket,
                field_name="approval_status",
                old_value=old_approval_status,
                new_value=ticket.approval_status,
            )

            db.session.commit()
            return {"message": "Ticket request has been cancelled"}, 200

        else:  # approval_status == "approve"

            form_data = ticket.details.copy() if ticket.details else {}

            if ticket.request_type == "Create Account":

                form_data.pop("security_questions", None)

                api_url = "http://localhost:5000/api/users"
                response = requests.post(api_url, json=form_data, cookies=request.cookies)

                new_user = response.json().get("user_id")

                form_data = {"security_questions": ticket.details["security_questions"]}

                for question in form_data["security_questions"]:
                    question["user_id"] = new_user

                api_url = f"http://localhost:5000/api/users/{new_user}/security_questions"
                requests.post(api_url, json=form_data, cookies=request.cookies)

                api_url = f"http://localhost:5000/api/users/{new_user}/profile"
                requests.post(api_url, json=None, cookies=request.cookies)

            elif ticket.request_type == "Delete Account":

                api_url = f"http://localhost:5000/api/users/{ticket.user_id}"
                requests.delete(api_url, json=None, cookies=request.cookies)

            elif ticket.request_type == "Change Role":

                api_url = f"http://localhost:5000/api/users/{ticket.user_id}"
                requests.put(api_url, json=form_data, cookies=request.cookies)

            elif ticket.request_type == "Edit Profile":

                api_url = f"http://localhost:5000/api/users/{ticket.user_id}/profile"
                requests.put(api_url, json=form_data, cookies=request.cookies)

            elif ticket.request_type == "Create Scholarship":

                form_data["donor_id"] = ticket.user_id

                api_url = "http://localhost:5000/api/scholarships"
                requests.post(api_url, json=form_data, cookies=request.cookies)

            elif ticket.request_type == "Update Scholarship":
                api_url = f"http://localhost:5000/api/scholarships/{form_data['scholarship_id']}"
                requests.put(api_url, json=form_data, cookies=request.cookies)

            elif ticket.request_type == "Delete Scholarship":
                api_url = f"http://localhost:5000/api/scholarships/{form_data['scholarship_id']}"
                requests.delete(api_url, json=None, cookies=request.cookies)

            elif ticket.request_type == "Update Application":
                api_url = f"http://localhost:5000/api/applications/{form_data['application_id']}"
                requests.put(api_url, json=form_data, cookies=request.cookies)

            elif ticket.request_type == "Delete Application":
                api_url = f"http://localhost:5000/api/applications/{form_data['application_id']}"
                requests.delete(api_url, json=None, cookies=request.cookies)

            elif ticket.request_type == "Update Application Score":
                api_url = f"http://localhost:5000/api/applications/{form_data['application_id']}/score"
                requests.put(api_url, json=form_data, cookies=request.cookies)

            elif ticket.request_type == "Reset Application Score":
                api_url = f"http://localhost:5000/api/applications/{form_data['application_id']}/score/reset"
                requests.put(api_url, json=None, cookies=request.cookies)

            old_status = ticket.status
            old_approval_status = ticket.approval_status

            ticket.approval_status = "Approved"
            ticket.approved_by = current_user.id
            ticket.approved_at = datetime.datetime.now(ZoneInfo("America/Phoenix"))
            ticket.status = "Closed - Approved"

            log_change(
                user_id=current_user_id_or_none(),
                action="Approved Ticket Request",
                entity=ticket,
                field_name="status",
                old_value=old_status,
                new_value=ticket.status,
            )
            log_change(
                user_id=current_user_id_or_none(),
                action="Approved Ticket Request",
                entity=ticket,
                field_name="approval_status",
                old_value=old_approval_status,
                new_value=ticket.approval_status,
            )

            db.session.commit()

            if ticket.request_type == "Create Account":
                msg = Message("SAS - Request Approved", recipients=[ticket.details["email"]])
                msg.body = f"Your request for {ticket.request_type} has been approved."
                mail.send(msg)
            else:
                msg = Message(
                    "SAS - Request Approved",
                    recipients=[User.query.filter_by(id=ticket.user_id).first().email],
                )
                msg.body = f"Your request for {ticket.request_type} has been approved."
                mail.send(msg)

            return {"message": "Ticket request has been approved"}, 200


class UserResource(Resource):

    UNF_error = "User not found"

    def get(self, user_id=None):
        if user_id:
            user = User.query.get(user_id)
            if not user:
                return {"message": self.UNF_error}, 404
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "net_id": user.net_id,
                "phone_num": user.phone_num,
                "user_type": user.user_type,
                "status": user.status
            }, 200
        else:
            users = User.query.all()
            return [{
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "net_id": u.net_id,
                "phone_num": u.phone_num,
                "user_type": u.user_type,
                "status": u.status
            } for u in users], 200

    def post(self):
        data = request.get_json()

        new_user = User()
        db.session.add(new_user)
        db.session.flush()

        field_map = {
            "username": "username",
            "email": "email",
            "first_name": "first_name",
            "last_name": "last_name",
            "net_id": "net_id",
            "phone_num": "phone_num",
            "user_type": "user_type",
            "status": "status",
        }

        for _, model_attr in field_map.items():
            new_val = getattr(new_user, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created User",
                entity=new_user,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )

        db.session.commit()
        return {"message": "User created", "user_id": new_user.id}, 201

    def put(self, user_id):
        user = User.query.get(user_id)
        if not user:
            return {"message": self.UNF_error}, 404

        data = request.get_json()

        field_map = {
            "username": "username",
            "email": "email",
            "password": "password",
            "first_name": "first_name",
            "last_name": "last_name",
            "net_id": "net_id",
            "phone_num": "phone_num",
            "user_type": "user_type",
            "status": "status",
        }

        invalid_keys = [k for k in data.keys() if k not in field_map]
        if invalid_keys:
            return {"message": f"Invalid input. Attribute(s) {invalid_keys} do not exist"}, 404

        clean_data = {k: v for k, v in data.items() if k in field_map}

        any_changed = apply_changes_with_audit(
            entity=user,
            data=clean_data,
            field_map=field_map,
            user_id=current_user_id_or_none(),
            action="Updated User",
            per_field=True,
        )

        if not any_changed:
            return {"message": "No changes applied"}, 200

        db.session.commit()
        return {"message": "User updated"}, 200

    def delete(self, user_id=None):
        user = User.query.get(user_id)
        if not user:
            return {"message": self.UNF_error}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted User",
            entity=user,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted"}, 200


class UserSecurityQuestionResource(Resource):

    def post(self, user_id):
        data = request.get_json()

        for question in data["security_questions"]:
            new_question = UserSecurityQuestion(
                user_id=user_id,
                question_id=question["question_id"],
                answer=question["answer"],
                question_num=question["question_num"],
            )
            db.session.add(new_question)

            db.session.flush()

            field_map = {
                "user_id": "user_id",
                "question_num": "question_num",
                "question_id": "question_id",
                "answer": "answer",
            }

            for _, model_attr in field_map.items():
                new_val = getattr(new_question, model_attr)
                log_change(
                    user_id=current_user_id_or_none(),
                    action="Created User Security Question",
                    entity=new_question,
                    field_name=model_attr,
                    old_value=None,
                    new_value=new_val,
                )

        db.session.commit()
        return {"message": "Security Questions set successfully"}, 200

    def get(self, user_id):
        security_questions = UserSecurityQuestion.query.filter_by(user_id=user_id).all()

        if not security_questions:
            return {"message": "No security questions found for this user"}, 404

        return [{
            "question_num": q.question_num,
            "question_id": q.question_id,
            "answer": q.answer
        } for q in security_questions], 200

    def put(self, user_id):
        data = request.get_json()

        if not data or "question_num" not in data or "question_id" not in data or "answer" not in data:
            return {"message": "Invalid request data"}, 400

        question_num = data["question_num"]
        question_id = data["question_id"]
        answer = data["answer"]

        user_question = UserSecurityQuestion.query.filter_by(
            user_id=user_id, question_num=question_num
        ).first()

        if not user_question:
            return {"message": f"Security question {question_num} not found for this user"}, 404

        old_qid = user_question.question_id
        old_answer = user_question.answer

        user_question.question_id = question_id
        user_question.answer = answer

        log_change(
            user_id=current_user_id_or_none(),
            action="Updated User Security Question",
            entity=user_question,
            field_name="question_id",
            old_value=old_qid,
            new_value=question_id,
        )
        log_change(
            user_id=current_user_id_or_none(),
            action="Updated User Security Question",
            entity=user_question,
            field_name="answer",
            old_value=old_answer,
            new_value=answer,
        )

        db.session.commit()
        return {"message": f"Security question {question_num} updated successfully"}, 200


class StudentProfileResource(Resource):
    def get(self, user_id):
        user_profile = StudentProfile.query.filter_by(user_id=user_id).first()

        if not user_profile:
            return {"message": "No student profile found for this user"}, 404

        return {
            "id": user_profile.id,
            "user_id": user_profile.user_id,
            "preferred_pronoun": user_profile.preferred_pronoun,
            "student_id": user_profile.student_id,
            "major": user_profile.major,
            "minor": user_profile.minor,
            "cumulative_gpa": user_profile.cumulative_gpa,
            "current_year": user_profile.current_year,
            "ethnicity": user_profile.ethnicity,
            "personal_statement_essay": user_profile.personal_statement_essay,
            "work_experience": user_profile.work_experience,
        }, 200

    def post(self, user_id):
        new_profile = StudentProfile(user_id=user_id)
        db.session.add(new_profile)

        db.session.flush()

        field_map = {
            "user_id": "user_id",
        }

        for _, model_attr in field_map.items():
            new_val = getattr(new_profile, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created Student Profile",
                entity=new_profile,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )

        db.session.commit()
        return {"message": "Student Profile created"}, 201

    def put(self, user_id):
        student_profile = StudentProfile.query.filter_by(user_id=user_id).first()
        if not student_profile:
            return {"message": "Student profile not found"}, 404

        data = request.get_json()

        field_map = {
            "preferred_pronoun": "preferred_pronoun",
            "student_id": "student_id",
            "major": "major",
            "minor": "minor",
            "cumulative_gpa": "cumulative_gpa",
            "current_year": "current_year",
            "ethnicity": "ethnicity",
            "personal_statement_essay": "personal_statement_essay",
            "work_experience": "work_experience",
        }

        invalid_keys = [k for k in data.keys() if k not in field_map]
        if invalid_keys:
            return {"message": f"Invalid input. Attribute(s) {invalid_keys} do not exist"}, 404

        clean_data = {k: v for k, v in data.items() if k in field_map}

        any_changed = apply_changes_with_audit(
            entity=student_profile,
            data=clean_data,
            field_map=field_map,
            user_id=current_user_id_or_none(),
            action="Updated Student Profile",
            per_field=True,
        )

        if not any_changed:
            return {"message": "No changes applied"}, 200

        db.session.commit()
        return {"message": "Student Profile updated"}, 200

    def delete(self, user_id):
        student_profile = StudentProfile.query.filter_by(user_id=user_id).first()
        if not student_profile:
            return {"message": "Student profile not found"}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted Student Profile",
            entity=student_profile,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(student_profile)
        db.session.commit()
        return {"message": "Student profile deleted"}, 200


class ScholarshipResource(Resource):

    SNF_error = "Scholarship not found"

    def get(self, schol_id=None):
        if schol_id:
            scholarship = Scholarship.query.get(schol_id)
            if not scholarship:
                return {"message": self.SNF_error}, 404
            return {
                "id": scholarship.id,
                "name": scholarship.name,
                "description": scholarship.description,
                "amount": str(scholarship.amount),
                "donor_id": scholarship.donor_id,
                "donor_name": scholarship.donor_name,
                "donor_phone": scholarship.donor_phone,
                "donor_email": scholarship.donor_email,
                "scholarships_available": scholarship.scholarships_available,
                "eligible_majors": scholarship.eligible_majors,
                "eligible_minors": scholarship.eligible_minors,
                "required_gpa": str(scholarship.required_gpa),
                "required_year": scholarship.required_year,
                "required_ethnicity": scholarship.required_ethnicity,
                "application_deadline": scholarship.application_deadline.isoformat()
                if scholarship.application_deadline
                else None,
                "other_requirements": scholarship.other_requirements,
            }, 200
        else:
            min_amount = request.args.get("min_amount", type=int)
            min_gpa = request.args.get("min_gpa", type=float)
            deadline_before = request.args.get("deadline_before", type=str)

            query = Scholarship.query
            if min_amount:
                query = query.filter(Scholarship.amount >= min_amount)
            if min_gpa:
                query = query.filter(Scholarship.required_gpa >= min_gpa)
            if deadline_before:
                query = query.filter(Scholarship.application_deadline <= deadline_before)

            scholarships = query.all()

            return [{
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "amount": str(s.amount),
                "donor_id": s.donor_id,
                "donor_name": s.donor_name,
                "donor_phone": s.donor_phone,
                "donor_email": s.donor_email,
                "scholarships_available": s.scholarships_available,
                "eligible_majors": s.eligible_majors,
                "eligible_minors": s.eligible_minors,
                "required_gpa": str(s.required_gpa),
                "required_year": s.required_year,
                "required_ethnicity": s.required_ethnicity,
                "application_deadline": s.application_deadline.isoformat()
                if s.application_deadline
                else None,
                "other_requirements": s.other_requirements,
            } for s in scholarships], 200

    def post(self):
        data = request.get_json()
        new_scholarship = Scholarship(
            name=data["name"],
            description=data["description"],
            amount=data["amount"],
            donor_id=data["donor_id"],
            donor_name=data["donor_name"],
            donor_phone=data["donor_phone"],
            donor_email=data["donor_email"],
            scholarships_available=data["scholarships_available"],
            eligible_majors=json.loads(data["eligible_majors"]) if data["eligible_majors"] else [],
            eligible_minors=json.loads(data["eligible_minors"]) if data["eligible_minors"] else [],
            required_gpa=data["required_gpa"],
            required_year=data["required_year"],
            required_ethnicity=data["required_ethnicity"],
            application_deadline=datetime.datetime.fromisoformat(data["application_deadline"]),
            other_requirements=data["other_requirements"],
        )
        db.session.add(new_scholarship)
        db.session.flush()

        field_map = {
            "name": "name",
            "description": "description",
            "amount": "amount",
            "donor_id": "donor_id",
            "donor_name": "donor_name",
            "donor_phone": "donor_phone",
            "donor_email": "donor_email",
            "scholarships_available": "scholarships_available",
            "eligible_majors": "eligible_majors",
            "eligible_minors": "eligible_minors",
            "required_gpa": "required_gpa",
            "required_year":"required_year",
            "required_ethnicity":"required_ethnicity",
            "application_deadline": "application_deadline",
            "other_requirements": "other_requirements",
        }

        for _, model_attr in field_map.items():
            new_val = getattr(new_scholarship, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created Scholarship",
                entity=new_scholarship,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )

        db.session.commit()

        all_students = User.query.filter_by(user_type="Student").all()

        for student in all_students:
            api_url = "http://localhost:5000/api/notifications"
            requests.post(
                api_url,
                json={
                    "user_id": student.id,
                    "title": "New Scholarship Created",
                    "message": f"Scholarship '{new_scholarship.name}' has been created. Check it out!",
                    "url": f"/student/scholarship-directory/{new_scholarship.id}",
                },
            )

            msg = Message("SAS - Notification", recipients=[student.email])
            msg.body = f"A new scholarship has been created '{new_scholarship.name}'. You should check it out!"
            mail.send(msg)

        return {"message": "Scholarship created"}, 201

    def put(self, schol_id):
        scholarship = Scholarship.query.get(schol_id)
        if not scholarship:
            return {"message": self.SNF_error}, 404

        data = request.get_json()
        clean_data = {}

        for key, value in data.items():
            if key == "scholarship_id":
                continue

            if not hasattr(scholarship, key):
                return {"message": f"Invalid input. Attribute '{key}' does not exist"}, 404

            if key == "application_deadline":
                clean_data[key] = datetime.datetime.fromisoformat(value) if value else None
            elif key in ("eligible_majors", "eligible_minors"):
                clean_data[key] = json.loads(value) if value else []
            else:
                clean_data[key] = None if value == "" else value

        field_map = {k: k for k in clean_data.keys()}

        any_changed = apply_changes_with_audit(
            entity=scholarship,
            data=clean_data,
            field_map=field_map,
            user_id=current_user_id_or_none(),
            action="Updated Scholarship",
            per_field=True,
        )

        if not any_changed:
            return {"message": "No changes applied"}, 200

        db.session.commit()
        return {"message": "Scholarship updated"}, 200

    def delete(self, schol_id=None):
        scholarship = Scholarship.query.get(schol_id)
        if not scholarship:
            return {"message": self.SNF_error}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted Scholarship",
            entity=scholarship,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(scholarship)
        db.session.commit()
        return {"message": "Scholarship deleted"}, 200


class ApplicationResource(Resource):

    ANF_error = "Application not found"

    def get(self, app_id=None):
        if app_id:
            application = Application.query.get(app_id)
            if not application:
                return {"message": self.ANF_error}, 404
            return {
                "id": application.id,
                "scholarship_id": application.scholarship_id,
                "user_id": application.user_id,
                "preferred_pronoun": application.preferred_pronoun,
                "student_id": application.student_id,
                "major": application.major,
                "minor": application.minor,
                "cumulative_gpa": str(application.cumulative_gpa),
                "current_year": application.current_year,
                "ethnicity": application.ethnicity,
                "personal_statement_essay": application.personal_statement_essay,
                "work_experience": application.work_experience,
                "date_submitted": application.date_submitted.isoformat(),
            }, 200
        else:
            applications = Application.query.all()
            return [{
                "id": a.id,
                "scholarship_id": a.scholarship_id,
                "user_id": a.user_id,
                "preferred_pronoun": a.preferred_pronoun,
                "student_id": a.student_id,
                "major": a.major,
                "minor": a.minor,
                "cumulative_gpa": str(a.cumulative_gpa),
                "current_year": a.current_year,
                "ethnicity": a.ethnicity,
                "personal_statement_essay": a.personal_statement_essay,
                "work_experience": a.work_experience,
                "date_submitted": a.date_submitted.isoformat(),
            } for a in applications], 200

    def post(self):
        data = request.get_json()

        application = Application.query.filter_by(
            scholarship_id=data["scholarship_id"],
            user_id=data["user_id"],
        ).first()
        if application:
            return {"message": "User has already applied for scholarship #" + str(data["scholarship_id"])}, 409

        new_application = Application(
            scholarship_id=data["scholarship_id"],
            user_id=data["user_id"],
            preferred_pronoun=data["preferred_pronoun"],
            student_id=data["student_id"],
            major=data["major"],
            minor=data["minor"],
            cumulative_gpa=data["cumulative_gpa"],
            current_year=data["current_year"],
            ethnicity=data["ethnicity"],
            personal_statement_essay=data["personal_statement_essay"],
            work_experience=data["work_experience"],
        )
        db.session.add(new_application)
        db.session.commit()

        field_map = {
            "scholarship_id": "scholarship_id",
            "user_id": "user_id",
            "preferred_pronoun": "preferred_pronoun",
            "student_id": "student_id",
            "major": "major",
            "minor": "minor",
            "cumulative_gpa": "cumulative_gpa",
            "current_year": "current_year",
            "ethnicity": "ethnicity",
            "personal_statement_essay": "personal_statement_essay",
            "work_experience": "work_experience",
            "date_submitted": "date_submitted",
        }

        for _, model_attr in field_map.items():
            new_val = getattr(new_application, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created Application",
                entity=new_application,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )

        new_score = ApplicationScore(
            application_id=new_application.id,
            scholarship_id=new_application.scholarship_id,
            score=calculate_matching_score(new_application.scholarship_id, new_application.id),
        )
        db.session.add(new_score)

        db.session.flush()

        score_field_map = {
            "application_id": "application_id",
            "scholarship_id": "scholarship_id",
            "score": "score",
            "is_overridden": "is_overridden",
        }

        for _, model_attr in score_field_map.items():
            new_val = getattr(new_score, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created Application Score",
                entity=new_score,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )


        db.session.commit()

        msg = Message(
            "SAS - Application Submitted",
            recipients=[User.query.filter_by(id=data["user_id"]).first().email],
        )
        msg.body = (
            f"Your application for '{new_application.scholarship.name}' has successfully been submitted and "
            f"is ready for review."
        )
        mail.send(msg)

        return {"message": "Application created", "id":new_application.id}, 201

    def put(self, app_id):
        application = Application.query.get(app_id)
        if not application:
            return {"message": self.ANF_error}, 404

        data = request.get_json()
        clean_data = {}

        for key, value in data.items():
            if key == "application_id":
                continue

            if not hasattr(application, key):
                return {"message": f"Invalid input. Attribute '{key}' does not exist"}, 404

            clean_data[key] = value

        field_map = {k: k for k in clean_data.keys()}

        any_changed = apply_changes_with_audit(
            entity=application,
            data=clean_data,
            field_map=field_map,
            user_id=current_user_id_or_none(),
            action="Updated Application",
            per_field=True,
        )

        if not any_changed:
            msg_text = None
        db.session.commit()

        if "status" in data:
            if data.get("status") == "Approved":
                msg = Message(
                    "SAS - Application Approved",
                    recipients=[User.query.filter_by(id=application.user_id).first().email],
                )
                msg.body = f"Your application for {application.scholarship.name} has been approved."
            elif data.get("status") == "Rejected":
                msg = Message(
                    "SAS - Application Rejected",
                    recipients=[User.query.filter_by(id=application.user_id).first().email],
                )
                msg.body = f"Your request for {application.scholarship.name} has been rejected."
            else:
                msg = None

            if msg:
                mail.send(msg)

        return {"message": "Application updated"}, 200

    def delete(self, app_id=None):
        application = Application.query.get(app_id)
        if not application:
            return {"message": self.SNF_error}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted Application",
            entity=application,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(application)
        db.session.commit()
        return {"message": "Application deleted"}, 200


class ApplicationScoreResource(Resource):

    ANF_error = "Application not found"

    def get(self, app_id=None):
        score = ApplicationScore.query.filter_by(application_id=app_id).first()
        if not score:
            return {"message": "No application score found for this application"}, 404
        return {
            "id": score.id,
            "application_id": score.application_id,
            "scholarship_id": score.scholarship_id,
            "score": score.score,
            "is_overridden": score.is_overridden,
        }, 200

    def post(self):
        data = request.get_json()
        new_application_score = ApplicationScore(
            application_id=data["application_id"],
            scholarship_id=data["scholarship_id"],
            score=calculate_matching_score(data["scholarship_id"], data["application_id"]),
        )
        db.session.add(new_application_score)
        db.session.flush()

        field_map = {
            "application_id": "application_id",
            "scholarship_id": "scholarship_id",
            "score": "score",
            "is_overridden": "is_overridden",
        }

        for _, model_attr in field_map.items():
            new_val = getattr(new_application_score, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Created Application Score",
                entity=new_application_score,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )

        db.session.commit()
        return {"message": "Application Score created"}, 201

    def put(self, app_id, action=None):
        score = ApplicationScore.query.filter_by(application_id=app_id).first()
        if not score:
            return {"message": self.ANF_error}, 404

        if action == "reset":
            old_score = score.score
            score.score = calculate_matching_score(score.scholarship.id, score.application.id)
            score.is_overridden = False

            log_change(
                user_id=current_user_id_or_none(),
                action="Reset Application Score",
                entity=score,
                field_name="score",
                old_value=old_score,
                new_value=score.score,
            )
        else:
            data = request.get_json()
            clean_data = {}

            for key, value in data.items():
                if key == "application_id":
                    continue
                if not hasattr(score, key):
                    return {"message": f"Invalid input. Attribute '{key}' does not exist"}, 404
                clean_data[key] = value

            field_map = {k: k for k in clean_data.keys()}

            apply_changes_with_audit(
                entity=score,
                data=clean_data,
                field_map=field_map,
                user_id=current_user_id_or_none(),
                action="Updated Application Score",
                per_field=True,
            )

        db.session.commit()
        return {"message": "Application Score updated"}, 200

    def delete(self, app_id=None):
        score = ApplicationScore.query.filter_by(application_id=app_id).first()
        if not score:
            return {"message": self.SNF_error}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted Application Score",
            entity=score,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(score)
        db.session.commit()
        return {"message": "Application Score deleted"}, 200


class NotificationResource(Resource):

    NNF_error = "Notification not found"

    def get(self, id=None):
        if id:
            notification = Notification.query.get(id)
            if not notification:
                return {"message": self.NNF_error}, 404
            return {
                "id": notification.id,
                "user_id": notification.user_id,
                "title": notification.title,
                "message": notification.message,
                "url": notification.url,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }, 200
        else:
            notifications = Notification.query.all()
            return [{
                "id": a.id,
                "user_id": a.user_id,
                "title": a.title,
                "message": a.message,
                "url": a.url,
                "is_read": a.is_read,
                "created_at": a.created_at.isoformat(),
            } for a in notifications], 200

    def delete(self, id=None):
        notification = Notification.query.get(id)
        if not notification:
            return {"message": self.NNF_error}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted Notification",
            entity=notification,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(notification)
        db.session.commit()
        return {"message": "Notification deleted"}, 200

    def post(self):
        data = request.get_json()
        new_notification = Notification(
            user_id=data["user_id"],
            title=data["title"],
            message=data["message"],
            url=data["url"]
        )
        db.session.add(new_notification)
        db.session.commit()
        return {"message": "Notification created"}, 201

    def put(self, id=None):
        notification = Notification.query.get(id)
        if not notification:
            return {"message": self.NNF_error}, 404

        data = request.get_json()
        clean_data = {}

        for key, value in data.items():
            if key == "id":
                continue
            if not hasattr(notification, key):
                return {"message": f"Invalid input. Attribute '{key}' does not exist"}, 404
            clean_data[key] = value

        field_map = {k: k for k in clean_data.keys()}

        any_changed = apply_changes_with_audit(
            entity=notification,
            data=clean_data,
            field_map=field_map,
            user_id=current_user_id_or_none(),
            action="Updated Notification",
            per_field=True,
        )

        if not any_changed:
            return {"message": "No changes applied"}, 200

        db.session.commit()
        return {"message": "Notification Updated"}, 200



class DocumentResource(Resource):

    
    DNF_error = "Document not found"

    def post(self):
        uploaded_file = request.files.get("document")
        application_id = request.form.get("application_id")
        document_type = request.form.get("document_type")

        if not application_id:
            return {"error": "application_id is required"}, 400

        if not uploaded_file or uploaded_file.filename == "":
            return {"error": "No file uploaded"}, 400

        filename = secure_filename(uploaded_file.filename)
        file_bytes = uploaded_file.read()

        document = Document(
            application_id=application_id,
            file_name=filename,
            file_type=document_type,
            file_data=file_bytes,
            mime_type=uploaded_file.mimetype,
        )

        db.session.add(document)
        db.session.flush()  # so document.id is populated

        # -------- AUDIT LOGGING (field_map style) -------- #
        field_map = {
            "application_id": "application_id",
            "file_name": "file_name",
            "file_type": "file_type",
            "mime_type": "mime_type"
        }

        for _, model_attr in field_map.items():
            new_val = getattr(document, model_attr)
            log_change(
                user_id=current_user_id_or_none(),
                action="Uploaded Document",
                entity=document,
                field_name=model_attr,
                old_value=None,
                new_value=new_val,
            )

        db.session.commit()

        return {"message": "Document uploaded successfully", "document_id": document.id}, 201
    
    def delete(self, id=None):
        document = Document.query.get(id)
        if not document:
            return {"message": self.NNF_error}, 404

        log_change(
            user_id=current_user_id_or_none(),
            action="Deleted Document",
            entity=document,
            field_name=None,
            old_value=None,
            new_value=None,
        )

        db.session.delete(document)
        db.session.commit()
        return {"message": "Document deleted"}, 200
    
    def get(self, id=None):
        if id:
            document = Document.query.get(id)
            if not document:
                return {"message": self.DNF_error}, 404
            return {
                "id": document.id,
                "application_id": document.application_id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "upload_date": document.upload_date.isoformat(),
                "mime_type": document.mime_type,
            }, 200
        else:
            documents = Document.query.all()
            return [{
                "id": document.id,
                "application_id": document.application_id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "upload_date": document.upload_date.isoformat(),
                "mime_type": document.mime_type,
            } for document in documents], 200