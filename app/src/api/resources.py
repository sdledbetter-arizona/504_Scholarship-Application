from flask_restful import Resource
from src.data.models import *

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
