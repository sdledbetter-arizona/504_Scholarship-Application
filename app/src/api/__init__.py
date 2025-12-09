from flask import Blueprint
from flask_restful import Api
from src.api.resources import *

api_bp = Blueprint("api", __name__)
api = Api(api_bp)


api.add_resource(TicketRequestResource, "/requests", "/requests/<int:request_id>", "/requests/<int:request_id>/<string:approval_status>")

api.add_resource(UserResource, "/users", "/users/<int:user_id>")
api.add_resource(UserSecurityQuestionResource, "/users/<int:user_id>/security_questions")
api.add_resource(StudentProfileResource, "/users/<int:user_id>/profile")

api.add_resource(ScholarshipResource, "/scholarships", "/scholarships/<int:schol_id>")
api.add_resource(ApplicationResource, "/applications", "/applications/<int:app_id>")
api.add_resource(ApplicationScoreResource, "/applications", "/applications/<int:app_id>/score","/applications/<int:app_id>/score/<string:action>")
api.add_resource(NotificationResource, "/notifications","/notifications/<int:id>")
api.add_resource(DocumentResource,"/documents", "/documents/<int:id>")