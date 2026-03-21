from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS

from .api.projects import projects_bp
from .api.reports import reports_bp
from .api.simulations import simulations_bp
from .api.tasks import tasks_bp
from .config import settings
from .db import init_db
from .services.task_service import TaskService
from .utils.logger import configure_logging


def create_app() -> Flask:
    configure_logging()
    init_db()
    TaskService.recover_incomplete_tasks()

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.max_content_length
    CORS(app)

    app.register_blueprint(projects_bp, url_prefix="/api/projects")
    app.register_blueprint(simulations_bp, url_prefix="/api/simulations")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")

    @app.get("/health")
    def health() -> tuple[dict[str, object], int]:
        return {
            "status": "ok",
            "app": "Miro_GPT",
            "database": settings.database_url,
            "storage_root": str(settings.data_dir),
        }, 200

    @app.errorhandler(413)
    def too_large(_: Exception) -> tuple[dict[str, str], int]:
        return {"error": "Uploaded file is too large."}, 413

    @app.errorhandler(Exception)
    def internal_error(error: Exception) -> tuple[dict[str, str], int]:
        return {"error": str(error)}, 500

    return app


def main() -> None:
    app = create_app()
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", "5001")),
        debug=settings.debug,
        threaded=True,
    )
