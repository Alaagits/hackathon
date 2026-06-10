def check_synthid_placeholder() -> dict:
    return {
        "checked": True,
        "status": "unavailable",
        "message": (
            "SynthID detection requires access to Google's detection API. "
            "This module is ready for future integration."
        ),
    }
