def calculate_final_risk(
    face_result: dict,
    deepfake_result: dict,
    watermark_result: dict,
    audio_result: dict,
) -> dict:
    face_score = face_result.get("face_match_score", 0)
    deepfake_score = deepfake_result.get("deepfake_score", 0)
    watermark_score = watermark_result.get("watermark_score", 0)
    audio_score = audio_result.get("audio_score", 0)

    face_mismatch_score = 100 - face_score

    final_score = round(
        0.30 * deepfake_score
        + 0.25 * face_mismatch_score
        + 0.25 * watermark_score
        + 0.20 * audio_score,
        2,
    )

    if final_score >= 70:
        risk_level = "high"
    elif final_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "final_risk_score": final_score,
        "risk_level": risk_level,
        "components": {
            "deepfake_score": deepfake_score,
            "face_mismatch_score": face_mismatch_score,
            "watermark_score": watermark_score,
            "audio_score": audio_score,
        },
        "weights": {
            "deepfake_score": 0.30,
            "face_mismatch_score": 0.25,
            "watermark_score": 0.25,
            "audio_score": 0.20,
        },
        "explanation": _generate_explanation(
            final_score, risk_level, face_score,
            deepfake_score, watermark_score, audio_score,
        ),
    }


def _generate_explanation(
    final_score: float,
    risk_level: str,
    face_score: float,
    deepfake_score: float,
    watermark_score: float,
    audio_score: float,
) -> dict:
    reasons: list[str] = []

    if face_score < 60:
        reasons.append("Face match is low compared to the verified employee profile.")
    if deepfake_score >= 60:
        reasons.append("Deepfake detection module found suspicious visual indicators.")
    if watermark_score >= 50:
        reasons.append("Watermark/provenance module found suspicious or AI-related signals.")
    if audio_score >= 60:
        reasons.append("Audio analysis found suspicious voice or lip-sync indicators.")
    if not reasons:
        reasons.append("No strong suspicious signal was detected across the analysed modules.")

    return {
        "summary": f"The final risk level is {risk_level} with a score of {final_score}/100.",
        "reasons": reasons,
    }
