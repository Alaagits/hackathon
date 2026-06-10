"""Web interface for the Deepfake Risk Pipeline — Facebook fake-profile detection."""

from flask import Flask, request, jsonify, render_template

from facebook.mock_search import search_facebook_profile
from facebook.detector import FakeProfileDetector, MAX_SCORE

app = Flask(__name__)
_detector = FakeProfileDetector()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze")
def analyze():
    return render_template("analyze.html")


@app.route("/api/detect-fake-profile", methods=["POST"])
def detect_fake_profile():
    body = request.get_json(silent=True) or {}
    employee_name = (body.get("employee_name") or "").strip()

    if not employee_name:
        return jsonify({"error": "employee_name is required"}), 400

    profile = search_facebook_profile(employee_name)
    score = _detector.calculate_risk_score(profile)
    classification = _detector.classify_profile(profile)
    reasons = _detector.get_detection_reasons(profile)

    return jsonify({
        "employee_name": employee_name,
        "risk_score": score,
        "max_score": MAX_SCORE,
        "classification": classification,
        "reasons": reasons,
        "criteria": {
            "has_profile_picture": profile.has_profile_picture,
            "friends_count": profile.friends_count,
            "posts_count": profile.posts_count,
            "has_basic_info": profile.has_basic_info,
            "suspicious_name": profile.suspicious_name,
            "low_interactions": profile.low_interactions,
            "no_mutual_connections": profile.no_mutual_connections,
            "employee_info_match": profile.employee_info_match,
            "posts_per_hour": profile.posts_per_hour,
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
