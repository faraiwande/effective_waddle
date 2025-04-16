import json, os, requests, base64, jwt
from datetime import datetime, timedelta
from flask import current_app, request, jsonify
from functools import wraps
from typing import Tuple, Any
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def base64url_decode(input_str: str) -> bytes:
    """Decode a base64url encoded string."""
    padding = '=' * (4 - len(input_str) % 4)  # Add padding
    return base64.urlsafe_b64decode(input_str + padding)

def get_jwks() -> dict:
    """Fetches JWKS from Auth0."""
    jwks_url = f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()

def get_auth_token() -> Tuple[str, str]:
    """
    Extracts and returns the access token from the Authorization header.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, "Access token is required and should start with 'Bearer '"
    return auth_header.split(' ')[1], None

def registration_token_verification(token):
    """
    verifies the access token by making a request to the Auth0 userinfo endpoint.
    """
    try:
        userinfo_endpoint = f"https://{current_app.config['AUTH0_DOMAIN']}/userinfo"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as http_err:
        current_app.logger.error(f"HTTP error occurred: {str(http_err)}")
        return None, f"HTTP error occurred: {str(http_err)}"
    except requests.exceptions.RequestException as req_err:
        current_app.logger.error(f"Request error occurred: {str(req_err)}")
        return None, f"Request error occurred: {str(req_err)}"
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return None, f"An error occurred: {str(e)}"


def verify_token(token: str) -> Tuple[dict, str]:
    """
    Decodes and verifies the JWT using the public key from Auth0.
    """
    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks['keys']:
            if key['kid'] == unverified_header['kid']:
                rsa_key = {
                    'kty': key['kty'],
                    'n': key['n'],
                    'e': key['e']
                }
                break

        if rsa_key:
            public_key = rsa.RSAPublicNumbers(
                int.from_bytes(base64url_decode(rsa_key['e']), 'big'),
                int.from_bytes(base64url_decode(rsa_key['n']), 'big')
            ).public_key(default_backend())

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=os.getenv('AUTH0_AUDIENCE'),
                issuer=f"https://{os.getenv('AUTH0_DOMAIN')}/"
            )
            return payload, None
        else:
            return None, "An unexpected error occurred."
    
    except jwt.ExpiredSignatureError:
        current_app.logger.error("Token has expired.")
        return None, "Token has expired."
    except jwt.InvalidTokenError as e:
        current_app.logger.error(f"Invalid token: {str(e)}")
        return None, "Invalid token."
    except Exception as e:
        current_app.logger.error("An unexpected error occurred")
        return None, "An unexpected error occurred."

def requires_auth(f: Any) -> Any:
    """
    decorator to ensure the route is accessed only with a valid authentication token.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token, error = get_auth_token()
        if error:
            return jsonify({"message": error}), 401

        user_info, error = verify_token(access_token)  # Call with token argument
        if error:
            return jsonify({"message": error}), 401

        request.user_info = user_info
        return f(*args, **kwargs)

    return decorated_function

