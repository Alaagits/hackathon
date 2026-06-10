class FacebookProfile:
    def __init__(
        self,
        has_profile_picture: bool,
        friends_count: int,
        posts_count: int,
        has_basic_info: bool,
        suspicious_name: bool,
        low_interactions: bool,
        no_mutual_connections: bool,
        employee_info_match: bool,
        posts_per_hour: float,
    ):
        self.has_profile_picture = has_profile_picture
        self.friends_count = friends_count
        self.posts_count = posts_count
        self.has_basic_info = has_basic_info
        self.suspicious_name = suspicious_name
        self.low_interactions = low_interactions
        self.no_mutual_connections = no_mutual_connections
        self.employee_info_match = employee_info_match
        self.posts_per_hour = posts_per_hour
