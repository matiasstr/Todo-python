import os
from datetime import datetime, timedelta, timezone

import jwt
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from database import configure_indexes, get_database


app = Flask(__name__)
CORS(app)

db = get_database()
configure_indexes(db)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "8"))


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def require_json():
    data = request.get_json(silent=True)
    if data is None:
        return None, error_response("Request body must be valid JSON.", 400)
    return data, None


def clean_email(email):
    return str(email or "").strip().lower()


def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
    }


def create_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_authorization_header():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")

    if scheme.lower() != "bearer" or not token:
        return None, error_response("Missing bearer token.", 401)

    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]), None
    except jwt.ExpiredSignatureError:
        return None, error_response("Token has expired.", 401)
    except jwt.InvalidTokenError:
        return None, error_response("Invalid token.", 401)


@app.get("/health")
def health():
    return jsonify({"service": "auth-service", "status": "ok"})


@app.post("/auth/register")
def register():
    data, error = require_json()
    if error:
        return error

    name = str(data.get("name", "")).strip()
    email = clean_email(data.get("email"))
    password = str(data.get("password", ""))

    if not name or not email or not password:
        return error_response("Name, email, and password are required.", 400)

    if len(password) < 6:
        return error_response("Password must be at least 6 characters.", 400)

    user = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
    }

    try:
        result = db.users.insert_one(user)
    except DuplicateKeyError:
        return error_response("An account with that email already exists.", 409)

    created_user = db.users.find_one({"_id": result.inserted_id})
    return jsonify(
        {
            "message": "User registered.",
            "user": serialize_user(created_user),
            "token": create_token(created_user),
        }
    ), 201


@app.post("/auth/login")
def login():
    data, error = require_json()
    if error:
        return error

    email = clean_email(data.get("email"))
    password = str(data.get("password", ""))

    if not email or not password:
        return error_response("Email and password are required.", 400)

    user = db.users.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return error_response("Invalid email or password.", 401)

    return jsonify(
        {
            "message": "Login successful.",
            "user": serialize_user(user),
            "token": create_token(user),
        }
    )


@app.get("/auth/me")
def me():
    claims, error = decode_authorization_header()
    if error:
        return error

    return jsonify(
        {
            "user": {
                "id": claims["sub"],
                "name": claims["name"],
                "email": claims["email"],
            }
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("AUTH_SERVICE_PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=True)
