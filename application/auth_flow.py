from core.exceptions import InvalidPasswordError, AuthenticationRequiredError

def register(username, password, db_session, session_service, registration_service):
    """
    Flow to register a new user.

    Steps:
        1. Check if registration is currently rate-limited for this username/IP.
        2. Attempt to register the user.
        3. If registration fails, increment the registration attempts counter.
        4. On success, reset registration attempts.

    Parameters:
        username (str): Username for the new user.
        password (str): Password for the new user.
        db_session: Database session object.
        session_service: SessionService instance.
        registration_service: Service implementing registration logic.

    Returns:
        dict: Result dictionary containing:
            - 'success' (bool): True if registration succeeded, False otherwise.
            - 'user' (optional): User object if registration succeeded.
            - 'error' (optional): Error message if registration failed.
    """
    from core.protection import check_register_rate_limit, apply_register_backoff, reset_register_attempts
    try:
        check_register_rate_limit(username, "127.0.0.1", db_session)

        user = registration_service.register(
            username=username,
            password=password,
            ip="127.0.0.1",
            db_session=db_session
        )

        # Registration successful → reset attempts
        reset_register_attempts(username, "127.0.0.1", db_session)
        return {"success": True, "user": user}

    except Exception as e:
        # Failed registration → increment attempts
        apply_register_backoff(username, "127.0.0.1", db_session)
        return {"success": False, "error": str(e)}


def login(username, password, db_session, session_service, authentication_service, user_service):
    """
    Flow to log in a user.

    Steps:
        1. Retrieve the user by username.
        2. Check if the user is currently locked or rate-limited.
        3. Attempt authentication.
        4. If authentication fails, increment the attempt counter and return 'Invalid credentials'.
        5. On successful authentication, reset attempts and set session.

    Parameters:
        username (str): Username to log in.
        password (str): Password to authenticate.
        db_session: Database session object.
        session_service: Instance of SessionService to manage user session.
        authentication_service: Service implementing authentication logic.
        user_service: Service to retrieve user data.

    Returns:
        dict: Result dictionary containing:
            - 'success' (bool): True if login succeeded, False otherwise.
            - 'user' (optional): User object if login succeeded.
            - 'access_token' (optional): Access token if login succeeded.
            - 'error' (optional): Error message if login failed.
    """
    # Retrieve user first
    user = user_service.get_user_by_username(username, db_session=db_session)
    if not user:
        return {"success": False, "error": "Invalid credentials."}

    # Check lock and rate-limit for existing user
    try:
        from core.protection import check_lock, check_rate_limit
        check_lock(user.id, "127.0.0.1", db_session)
        check_rate_limit(user.id, "127.0.0.1", db_session)
    except AuthenticationRequiredError as e:
        return {"success": False, "error": f"Login blocked or rate-limited: {e}"}

    # Attempt login
    try:
        tokens = authentication_service.login(
            username=username,
            password=password,
            ip="127.0.0.1",
            db_session=db_session
        )
    except Exception:
        # Wrong password → increment attempts but do NOT show rate-limit message
        from core.protection import apply_backoff
        apply_backoff(user.id, "127.0.0.1", db_session)
        return {"success": False, "error": "Invalid credentials."}

    # Successful login → reset attempts and set session
    from core.protection import reset_attempts
    reset_attempts(user.id, "127.0.0.1", db_session)

    session_service.set_session(
        user,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token")
    )

    return {"success": True, "user": user, "access_token": tokens.get("access_token")}