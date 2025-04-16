from flask import Blueprint, request, jsonify
from auth_service.utils.auth_utils import *
from auth_service.models.user import db, BaseUser, RoleUpdate

reg_bp = Blueprint('reg_bp', __name__)

@reg_bp.route('/user/registration', methods=['GET'])
def user_registration():
    """
    User registration endpoint.
    """
    access_token, error = get_auth_token()
    if error:
        return jsonify({"message": error}), 400

    user_login_info, error = registration_token_verification(access_token)
    if error:
        return jsonify({"message": error}), 403

    user_sub = user_login_info['sub']
    user_name = user_login_info.get('name')
    user_email = user_login_info.get('email')
    user_picture = user_login_info.get('picture')

    base_user = BaseUser.query.filter_by(sub=user_sub).first()

    if not base_user:
        base_user = BaseUser(
            sub=user_sub,
            name=user_name,
            email=user_email,
            picture=user_picture
        )
        db.session.add(base_user)
        db.session.commit()

    return jsonify({
        "sub": base_user.sub,
        "name": base_user.name,
        "email": base_user.email,
        "picture": base_user.picture,
        "is_service_provider": base_user.is_service_provider,
        "user_rating": base_user.user_rating,
        "weekly_schedule": base_user.weekly_schedule,
        "message": "Registration Successful"
    }), 200


user_information_bp = Blueprint('ui_bp', __name__)

@user_information_bp.route('/user/information/service_provider', methods=['GET'])
@requires_auth
def get_user_service_provider_information():
    user_info = request.user_info
    user_sub = user_info['sub']
    
    user = BaseUser.query.filter_by(sub=user_sub).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    if not user.is_service_provider:
        return jsonify({"message": "User is not a service provider"}), 403
    
    
    return jsonify({
        "sub": user.sub,
        "name": user.name,
        "email": user.email,
        "picture": user.picture,
        "user_rating": user.user_rating,
        "weekly_schedule": user.weekly_schedule
    }), 200
    
    
@user_information_bp.route('/user/information/service_user', methods=['GET'])
@requires_auth
def get_user_service_user_information():
    user_info = request.user_info
    user_sub = user_info['sub']
    
    user = BaseUser.query.filter_by(sub=user_sub).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    if user.is_service_provider:
        return jsonify({"message": "User is a service provider"}), 403
    
    return jsonify({
        "sub": user.sub,
        "name": user.name,
        "email": user.email,
        "picture": user.picture,
        "user_rating": user.user_rating,
        "weekly_schedule": user.weekly_schedule
    }), 200

    

   
