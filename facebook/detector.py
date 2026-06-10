from .profile import FacebookProfile

# Maximum theoretical score (all flags triggered) = 155
MAX_SCORE = 155


class FakeProfileDetector:

    def calculate_risk_score(self, profile: FacebookProfile) -> int:
        score = 0

        if not profile.has_profile_picture:
            score += 20

        if profile.friends_count < 10:
            score += 20

        if profile.posts_count < 5:
            score += 20

        if not profile.has_basic_info:
            score += 15

        if profile.suspicious_name:
            score += 10

        if profile.low_interactions:
            score += 15

        if profile.no_mutual_connections:
            score += 10

        if not profile.employee_info_match:
            score += 25

        if profile.posts_per_hour >= 10:
            score += 20

        return score

    def classify_profile(self, profile: FacebookProfile) -> str:
        score = self.calculate_risk_score(profile)

        if score >= 60:
            return "LIKELY_FAKE"
        elif score >= 30:
            return "SUSPICIOUS"
        else:
            return "LIKELY_REAL"

    def get_detection_reasons(self, profile: FacebookProfile) -> list[str]:
        reasons = []

        if not profile.has_profile_picture:
            reasons.append("No profile picture")

        if profile.friends_count < 10:
            reasons.append(f"Very few friends ({profile.friends_count})")

        if profile.posts_count < 5:
            reasons.append(f"Very few posts ({profile.posts_count})")

        if not profile.has_basic_info:
            reasons.append("Missing basic profile information")

        if profile.suspicious_name:
            reasons.append("Suspicious profile name")

        if profile.low_interactions:
            reasons.append("Low interactions on posts")

        if profile.no_mutual_connections:
            reasons.append("No mutual connections with employee or organisation")

        if not profile.employee_info_match:
            reasons.append("Profile information does not match employee records")

        if profile.posts_per_hour >= 10:
            reasons.append(f"Abnormal posting frequency ({profile.posts_per_hour:.0f} posts/hour)")

        return reasons
