from flask import Blueprint
from flask_restful import Api
from src.api.resources import *

api_bp = Blueprint("api", __name__)
api = Api(api_bp)

api.add_resource(UserResource, "/users", "/users/<int:user_id>")