import os
import json
import math
import numpy as np

from flask import Flask, request, jsonify, render_template, Response, g

from src.core.data_loader import load_excel
from src.core.metrics_calculator import MetricsCalculator
from src.visualization import chart_generator as cg
from src.utils.helpers import rows_to_csv, rows_to_report


def _sanitize(obj):
    """Recursively replace NaN/Inf with None so json.dumps never chokes."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    return obj


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "..", "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
    app.config["UPLOADED_DATA"] = []

    calculator = MetricsCalculator()

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/upload", methods=["POST"])
    def upload():
        if "file" not in request.files:
            return jsonify({"error": "未选择文件"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "文件名为空"}), 400

        # Save to a temp path
        import tempfile
        suffix = os.path.splitext(file.filename)[1] or ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            rows = load_excel(tmp_path)
        except Exception as exc:
            return jsonify({"error": f"文件解析失败: {str(exc)}"}), 422
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # Attach metrics to each row
        for row in rows:
            row["metrics"] = calculator.calculate(row)

        app.config["UPLOADED_DATA"] = rows

        # Build serialisable summary (exclude large numpy arrays)
        summary = []
        for i, row in enumerate(rows):
            summary.append({
                "idx": i,
                "material": row.get("material"),
                "gas": row.get("gas"),
                "concentration": row.get("concentration"),
                "temperature": row.get("temperature"),
                "humidity": row.get("humidity"),
                "inject_time": row.get("inject_time"),
                "extract_time": row.get("extract_time"),
                "metrics": row.get("metrics", {}),
            })

        return jsonify(_sanitize({"count": len(rows), "rows": summary}))

    @app.route("/chart/<chart_type>")
    def chart(chart_type):
        data = app.config.get("UPLOADED_DATA", [])
        row_idx = request.args.get("row", 0, type=int)

        handlers = {
            "response":    lambda: cg.response_curve(data, row_idx),
            "sensitivity": lambda: cg.sensitivity_curve(data),
            "selectivity": lambda: cg.selectivity_chart(data),
            "temperature": lambda: cg.temperature_heatmap(data),
            "humidity":    lambda: cg.humidity_chart(data),
            "radar":       lambda: cg.radar_chart(data),
        }

        handler = handlers.get(chart_type)
        if handler is None:
            return jsonify({"error": f"未知图表类型: {chart_type}"}), 404

        try:
            chart_json = handler()
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

        return Response(chart_json, mimetype="application/json")

    @app.route("/export/csv", methods=["POST"])
    def export_csv():
        data = app.config.get("UPLOADED_DATA", [])
        csv_text = rows_to_csv(data)
        return Response(
            csv_text,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=gas_sensor_metrics.csv"},
        )

    @app.route("/export/report", methods=["POST"])
    def export_report():
        data = app.config.get("UPLOADED_DATA", [])
        report_text = rows_to_report(data)
        return Response(
            report_text,
            mimetype="text/plain; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=gas_sensor_report.txt"},
        )

    return app
