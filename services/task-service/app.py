import os

import jwt
from bson import ObjectId
from flask import Flask, jsonify, request
from flask_cors import CORS

from database import configure_indexes, get_database


app = Flask(__name__)
CORS(app)

db = get_database()
configure_indexes(db)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


def require_json():
    data = request.get_json(silent=True)
    if data is None:
        return None, error_response("Request body must be valid JSON.", 400)
    return data, None


def current_user_claims():
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


def parse_object_id(value, field_name="id"):
    if not ObjectId.is_valid(str(value)):
        return None, error_response(f"Invalid {field_name}.", 400)
    return ObjectId(str(value)), None


def serialize_task(task):
    return {
        "id": str(task["_id"]),
        "user_id": task["user_id"],
        "title": task["title"],
        "completed": bool(task.get("completed", False)),
    }


@app.get("/health")
def health():
    return jsonify({"service": "task-service", "status": "ok"})


@app.get("/tasks")
def list_tasks():
    claims, error = current_user_claims()
    if error:
        return error

    tasks = db.tasks.find({"user_id": claims["sub"]}).sort("_id", -1)
    return jsonify({"tasks": [serialize_task(task) for task in tasks]})


@app.post("/tasks")
def create_task():
    claims, error = current_user_claims()
    if error:
        return error

    data, error = require_json()
    if error:
        return error

    title = str(data.get("title", "")).strip()
    if not title:
        return error_response("Task title is required.", 400)

    result = db.tasks.insert_one(
        {
            "user_id": claims["sub"],
            "title": title,
            "completed": False,
        }
    )
    task = db.tasks.find_one({"_id": result.inserted_id})
    return jsonify({"message": "Task created.", "task": serialize_task(task)}), 201


@app.put("/tasks/<task_id>")
def update_task(task_id):
    claims, error = current_user_claims()
    if error:
        return error

    task_object_id, error = parse_object_id(task_id, "task_id")
    if error:
        return error

    data, error = require_json()
    if error:
        return error

    updates = {}
    if "title" in data:
        title = str(data.get("title", "")).strip()
        if not title:
            return error_response("Task title cannot be empty.", 400)
        updates["title"] = title

    if "completed" in data:
        updates["completed"] = bool(data.get("completed"))

    if not updates:
        return error_response("No supported fields were provided.", 400)

    db.tasks.update_one(
        {"_id": task_object_id, "user_id": claims["sub"]},
        {"$set": updates},
    )
    task = db.tasks.find_one({"_id": task_object_id, "user_id": claims["sub"]})
    if not task:
        return error_response("Task not found.", 404)

    return jsonify({"message": "Task updated.", "task": serialize_task(task)})


@app.delete("/tasks/<task_id>")
def delete_task(task_id):
    claims, error = current_user_claims()
    if error:
        return error

    task_object_id, error = parse_object_id(task_id, "task_id")
    if error:
        return error

    result = db.tasks.delete_one({"_id": task_object_id, "user_id": claims["sub"]})
    if result.deleted_count == 0:
        return error_response("Task not found.", 404)

    return jsonify({"message": "Task deleted."})


if __name__ == "__main__":
    port = int(os.getenv("TASK_SERVICE_PORT", "5002"))
    app.run(host="127.0.0.1", port=port, debug=True)
