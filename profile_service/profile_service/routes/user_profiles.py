from flask import Blueprint, request, jsonify
from profile_service.utils.auth_utils import *
from profile_service.models.user_profile_model import db, BaseUser, RoleUpdate
from profile_service.utils.s3_utils import upload_image_to_s3
from datetime import datetime

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

    

role_bp = Blueprint('role_bp', __name__)

@role_bp.route('/user/role_update', methods=['PATCH'])
@requires_auth
def update_service_provider_status():
    user_info = request.user_info
    user_sub = user_info['sub']

    data = request.get_json()
    if not data or 'is_service_provider' not in data:
        return jsonify({"message": "Missing 'is_service_provider' field"}), 400

    desired_role = data['is_service_provider']
    user = BaseUser.query.filter_by(sub=user_sub).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    if user.is_service_provider == desired_role:
        return jsonify({"message": "User already has this role"}), 400

    if desired_role is True:
        # PROMOTION: Require location + mobile number
        required_fields = ['address_line1', 'city', 'country', 'latitude', 'longitude', 'mobile_number']
        if not all(field in data for field in required_fields):
            return jsonify({"message": "Missing one or more required fields for service provider promotion"}), 400

        lat = data['latitude']
        lon = data['longitude']
        if not (-90 <= lat <= 90):
            return jsonify({"message": "Latitude must be between -90 and 90"}), 400
        if not (-180 <= lon <= 180):
            return jsonify({"message": "Longitude must be between -180 and 180"}), 400

        user.is_service_provider = True
        user.address_line1 = data['address_line1']
        user.address_line2 = data.get('address_line2')
        user.city = data['city']
        user.province_or_state = data.get('province_or_state')
        user.postal_code = data.get('postal_code')
        user.country = data['country']
        user.latitude = lat
        user.longitude = lon
        user.mobile_number = data['mobile_number']

        message = "User successfully promoted to service provider"

    else:
        # DEMOTION: Clear location & mobile number
        if any(field in data for field in ['address_line1', 'latitude', 'longitude', 'mobile_number']):
            return jsonify({"message": "Extra fields not allowed when demoting to regular user"}), 400

        user.is_service_provider = False
        user.address_line1 = None
        user.address_line2 = None
        user.city = None
        user.province_or_state = None
        user.postal_code = None
        user.country = None
        user.latitude = None
        user.longitude = None
        user.mobile_number = None

        message = "User successfully demoted to regular user"

    user.updated_at = datetime.utcnow()

    role_update = RoleUpdate(
        sub=user_sub,
        is_service_provider=desired_role
    )

    db.session.add(user)
    db.session.add(role_update)
    db.session.commit()

    return jsonify({
        "message": message,
        "sub": user.sub,
        "is_service_provider": user.is_service_provider,
        "mobile_number": user.mobile_number,
        "role_updated_at": role_update.created_at
    }), 200


profile_bp = Blueprint('profile_bp', __name__)

@profile_bp.route('/user/profile', methods=['PATCH'])
@requires_auth
def update_user_profile():
    """
    Update name, email, and optionally upload a new profile picture to S3.
    Supports form-data or JSON input.
    """
    user_info = request.user_info
    user_sub = user_info['sub']

    if request.content_type.startswith('multipart/form-data'):
        data = request.form
        image = request.files.get('image')
    else:
        data = request.get_json()
        image = None

    user = BaseUser.query.filter_by(sub=user_sub).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    if 'name' in data and data['name'].strip():
        user.name = data['name']

    if 'email' in data and data['email'].strip():
        new_email = data['email']
        if BaseUser.query.filter(BaseUser.email == new_email, BaseUser.sub != user_sub).first():
            return jsonify({"message": "Email is already in use"}), 400
        user.email = new_email

    if image:
        try:
            image_url = upload_image_to_s3(image)
            user.picture = image_url
        except Exception as e:
            return jsonify({"message": f"Image upload failed: {str(e)}"}), 500

    user.updated_at = datetime.utcnow()
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully",
        "sub": user.sub,
        "name": user.name,
        "email": user.email,
        "picture": user.picture
    }), 200