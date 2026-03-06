class SessionService:
    """
    Session service that encapsulates a session manager.
    Fully decoupled from the core by requiring a session manager to be injected.
    """

    def __init__(self, session_manager):
        """
        Parameters:
            session_manager: A session manager implementing the required interface.
                             Must be provided by the composition root (CLI or app layer).
        """
        if session_manager is None:
            raise ValueError("A session_manager must be provided")
        self._session = session_manager

    def set_session(self, user, access_token=None, refresh_token=None):
        """Set the session for a user with optional tokens."""
        self._session.set(user, access_token, refresh_token)

    def clear_session(self):
        """Clear the current session."""
        self._session.clear()

    @property
    def current_user(self):
        """Return the current user of the session, or None if not logged in."""
        return getattr(self._session, "current_user", None)

    @property
    def logged_in(self):
        """Return True if a user is logged in, False otherwise."""
        return self._session.logged_in