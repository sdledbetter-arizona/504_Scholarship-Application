from functools import wraps
from flask import redirect, url_for, request, flash
from flask_login import current_user
from src.models import Scholarship, Application, ApplicationScore, StudentProfile, User, AuditLog
from src import db
from typing import Mapping


def logout_required(route_function):
    @wraps(route_function)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('views.home'))
        return route_function(*args, **kwargs)
    return decorated_view

def admin_required(route_function):
    @wraps(route_function)
    def decorated_view(*args, **kwargs):
        if current_user.user_type != 'Scholarship Admin':
            flash("You do not have permission to access that page.", "danger")
            return redirect(request.referrer or url_for("views.home"))
        return route_function(*args, **kwargs)
    return decorated_view

def student_required(route_function):
    @wraps(route_function)
    def decorated_view(*args, **kwargs):
        if current_user.user_type != 'Student':
            flash("You do not have permission to access that page.", "danger")
            return redirect(request.referrer or url_for("views.home"))
        return route_function(*args, **kwargs)
    return decorated_view

def donor_required(route_function):
    @wraps(route_function)
    def decorated_view(*args, **kwargs):
        if current_user.user_type != 'Scholarship Donor':
            flash("You do not have permission to access that page.", "danger")
            return redirect(request.referrer or url_for("views.home"))
        return route_function(*args, **kwargs)
    return decorated_view

def check_not_applied(route_function):
    @wraps(route_function)
    def decorated_view(*args, **kwargs):
        scholarship_id = kwargs.get("id")
        if Application.query.filter_by(scholarship_id = scholarship_id, user_id = current_user.id).first():
            flash("You have already applied for this scholarship.", "danger")
            return redirect(request.referrer or url_for("student.applications"))
        return route_function(*args, **kwargs)
    return decorated_view


def log_change(
    *,
    user_id: int | None,
    action: str,
    entity,
    field_name: str | None = None,
    old_value=None,
    new_value=None,
    extra: dict | None = None,
):
    """Low-level logger used by apply_changes_with_audit."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=entity.id,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None
    )
    db.session.add(log)


def apply_changes_with_audit(
    *,
    entity,
    data: Mapping[str, object],
    field_map: Mapping[str, str],
    user_id: int | None,
    action: str,
    per_field: bool = True,
) -> bool:
    
    changes: dict[str, dict[str, object]] = {}
    any_changed = False

    for form_field, model_attr in field_map.items():
        if form_field not in data:
            continue

        new_val = data[form_field]
        old_val = getattr(entity, model_attr)

        # Basic conversion example for numeric fields; adjust as needed
        if isinstance(old_val, (int, float)) and isinstance(new_val, str):
            if new_val == "":
                new_val = None
            else:
                try:
                    new_val = type(old_val)(new_val)
                except ValueError:
                    # Skip invalid conversion; you might want to handle validation elsewhere
                    continue

        if old_val != new_val:
            any_changed = True
            setattr(entity, model_attr, new_val)
            changes[model_attr] = {"old": old_val, "new": new_val}

            if per_field:
                log_change(
                    user_id=user_id,
                    action=action,
                    entity=entity,
                    field_name=model_attr,
                    old_value=old_val,
                    new_value=new_val
                )

    if not per_field and changes:
        log_change(
            user_id=user_id,
            action=action,
            entity=entity,
            field_name=None,
            old_value=None,
            new_value=None
        )

    return any_changed


def calculate_matching_score(scholarship_id, application_id):

    scholarship_requirements = Scholarship.query.filter_by(id=scholarship_id).first().requirements
    applicant_profile = Application.query.filter_by(id=application_id).first().results

    scholarship_requirements = {key: value for key, value in scholarship_requirements.items() if value is not None}
    applicant_profile = {key: value for key, value in applicant_profile.items() if value is not None}

    total_requirements = len(scholarship_requirements)

    matched_requirements = 0

    for key, value in scholarship_requirements.items():
        if key == "gpa" and applicant_profile.get(key, 0) >= value:
            matched_requirements += 1
        elif key in ["major", "minor"]:
            profile_value = applicant_profile.get(key)

            if profile_value in value:
                matched_requirements += 1

        elif key not in ["gpa", "major", "minor"] and applicant_profile.get(key) == value:
            matched_requirements += 1
    
    missed_requirements = total_requirements - matched_requirements
    
    if missed_requirements == 0:
        return 5
    elif missed_requirements == 1:
        return 4
    elif missed_requirements == 2:
        return 3
    elif missed_requirements == 3:
        return 2
    elif missed_requirements == 4:
        return 1
    else:
        return 0