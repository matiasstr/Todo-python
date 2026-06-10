import os

import requests
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS


app = Flask(__name__, static_folder="../../frontend", static_url_path="")
CORS(app)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://127.0.0.1:5001")
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://127.0.0.1:5002")
TIMEOUT_SECONDS = float(os.getenv("GATEWAY_TIMEOUT_SECONDS", "5"))


def proxy_request(base_url, path):
    url = f"{base_url}{path}"
    headers = {}

    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]

    try:
        upstream_response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            json=request.get_json(silent=True),
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return jsonify({"error": "Upstream service is unavailable."}), 503

    excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
    response_headers = [
        (name, value)
        for name, value in upstream_response.headers.items()
        if name.lower() not in excluded_headers
    ]

    return Response(
        upstream_response.content,
        status=upstream_response.status_code,
        headers=response_headers,
    )


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"service": "api-gateway", "status": "ok"})


@app.route("/api/auth/<path:path>", methods=["GET", "POST"])
def auth_proxy(path):
    return proxy_request(AUTH_SERVICE_URL, f"/auth/{path}")


@app.route("/api/tasks", methods=["GET", "POST"])
def tasks_proxy():
    return proxy_request(TASK_SERVICE_URL, "/tasks")


@app.route("/api/tasks/<task_id>", methods=["PUT", "DELETE"])
def task_detail_proxy(task_id):
    return proxy_request(TASK_SERVICE_URL, f"/tasks/{task_id}")


if __name__ == "__main__":
    port = int(os.getenv("GATEWAY_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
