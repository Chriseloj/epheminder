class SessionManager:
    def __init__(self):
        self.current_user = None
        self.access_token = None
        self.refresh_token = None

    @property
    def logged_in(self):
        return self.access_token is not None

    def set(self, user, access_token, refresh_token):
        self.current_user = user
        self.access_token = access_token
        self.refresh_token = refresh_token

    def clear(self):
        self.current_user = None
        self.access_token = None
        self.refresh_token = None

session_manager = SessionManager()