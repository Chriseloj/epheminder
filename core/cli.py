import sys
from getpass import getpass
from core.services import ReminderService, UserService
from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.security import Role, decode_token
from infrastructure.storage import get_db_session
from core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from infrastructure.repositories import ReminderRepository
from core.exceptions import ReminderTextTooLongError, InvalidExpirationError, MaxRemindersReachedError
from core.logout import logout as logout_service
import logging
logger = logging.getLogger(__name__)

db_session = get_db_session()

# ------------------------------
# Session Management
# ------------------------------
current_token = None
current_user = None  # cached user object
current_refresh_token = None

def set_current_session(user, access_token, refresh_token):
    global current_user, current_token, current_refresh_token
    current_user = user
    current_token = access_token
    current_refresh_token = refresh_token

def clear_session():
    global current_user, current_token, current_refresh_token
    current_user = None
    current_token = None
    current_refresh_token = None

# ------------------------------
# Helper functions
# ------------------------------
def safe_input(prompt):
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        sys.exit(0)

def safe_print(msg):
    print(msg)

def require_login(func):
    """Decorator: require valid JWT login."""
    def wrapper(*args, **kwargs):
        if not current_token:
            safe_print("You must be logged in first.")
            return
        try:
            payload = decode_token(current_token)
            # refresh user cache
            user_id = payload["sub"]
            global current_user
            current_user = UserService.get_user_by_id(user_id, db_session=db_session)
        except AuthenticationRequiredError:
            safe_print("Session expired. Please login again.")
            clear_session()
            return
        except Exception:
            safe_print("Invalid session. Please login again.")
            clear_session()
            return
        return func(*args, **kwargs)
    return wrapper

# ------------------------------
# CLI Actions
# ------------------------------
def register_user():
    safe_print("=== Register ===")
    username = safe_input("Username: ")
    password = getpass("Password: ")
    ip = "127.0.0.1"

    try:
        user = RegistrationService.register(
            username=username,
            password=password,
            ip=ip,
            role=Role.USER,
            db_session=db_session
        )
        safe_print(f"User {user.username} registered successfully.")
    except Exception as e:
        safe_print(f"Registration failed")

def login_user():

    if current_token:
        safe_print("Already logged in. Please logout first.")
        return
    safe_print("=== Login ===")
    username = safe_input("Username: ")
    password = getpass("Password: ")
    ip = "127.0.0.1"  # CLI local

    try:
        tokens = AuthenticationService.login(
            username=username,
            password=password,
            ip=ip,
            db_session=db_session
        )
        user = UserService.get_user_by_username(username, db_session=db_session)
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")  # None on tests

        set_current_session(
            user,
            access_token,
            refresh_token
        )
        safe_print("Login successful.")
    except AuthenticationRequiredError as e:
        safe_print(f"Login blocked or rate-limited: {e}")
    except Exception as e:
        safe_print(f"Login failed: {e}")
        
@require_login
def create_reminder():
    safe_print("=== Create Reminder ===")
    text = safe_input("Reminder text: ")
    try:
        amount = int(safe_input("Expires in amount: "))
    except ValueError:
        safe_print("Expiration amount must be a number.")
        return
    unit = safe_input("Unit (minutes/hours/days): ")

    repo = ReminderRepository(db_session)
    try:
        reminder = ReminderService.create_reminder(
            user=current_user,
            text=text,
            amount=amount,
            unit=unit,
            reminder_repo=repo
        )
        safe_print(f"Reminder created. ID: {reminder.id}")

    except ReminderTextTooLongError as e:
        safe_print(f"Reminder text too long (max {e.max_length} chars).")
    except MaxRemindersReachedError as e:
        safe_print(f"You have reached the maximum of {e.max_reminders} reminders.")
    except InvalidExpirationError as e:
        safe_print(f"Invalid expiration: {e}")
    except Exception as e:
        logger.exception("Error creating reminder")
        safe_print("Failed to create reminder. Please try again later.")

@require_login
def list_reminders():
    safe_print("=== List Reminders ===")
    try:
        
        repo = ReminderRepository(db_session)
        reminders = ReminderService.list_reminders(current_user, reminder_repo=repo)
        if not reminders:
            safe_print("No active reminders.")
            return
        for r in reminders:
            safe_print(f"- ID: {r.id} | Text: {r.text} | Expires: {r.expires_at}")
   
    except InvalidExpirationError as e:
        safe_print(f"Invalid expiration: {e}")
    except PermissionDeniedError:
        safe_print("Permission denied for listing reminders.")
    except Exception as e:
        logger.exception("Error list reminder")  # stack trace to log
        safe_print("Failed to list reminder. Please check your input or try again later.")

@require_login
def delete_reminder():
    safe_print("=== Delete Reminder ===")
    
    reminder_id = safe_input("Reminder ID: ")

    if isinstance(reminder_id, str) and reminder_id.isdigit():
        reminder_id = int(reminder_id)

    try:
        repo = ReminderRepository(db_session)
        success = ReminderService.delete_reminder(
            current_user,
            reminder_id,
            reminder_repo=repo
        )

        if success:
            safe_print("Reminder deleted successfully.")
        else:
            safe_print("Reminder not found.")

    except PermissionDeniedError:
        safe_print("Permission denied for deleting reminders.")
    except Exception:
        logger.exception("Error delete reminder")
        safe_print("Failed to delete reminder. Please try again later.")

def logout():
    global current_token, current_refresh_token

    if not current_token:
        safe_print("You are not logged in.")
        return

    try:
        logout_service(
            refresh_token=current_refresh_token,
            access_token=current_token,
            db_session=db_session
        )
    except Exception:
        logger.exception("Error during logout")

    clear_session()
    safe_print("Logged out successfully.")

def exit_app():
    try:
        db_session.close()
    except Exception:
        logger.exception("Error closing DB session")

    safe_print("Exiting.")
    sys.exit(0)
# ------------------------------
# CLI Menu
# ------------------------------
menu = {
    "1": ("Register", register_user),
    "2": ("Login", login_user),
    "3": ("Create Reminder", create_reminder),
    "4": ("List Reminders", list_reminders),
    "5": ("Delete Reminder", delete_reminder),
    "6": ("Logout", logout),
    "0": ("Exit", exit_app)
}

def run_cli():
    while True:
        safe_print("\n--- Main Menu ---")
        for k, (desc, _) in menu.items():
            safe_print(f"{k}. {desc}")
        choice = safe_input("Choose an option: ")
        action = menu.get(choice)
        if action:
            action[1]()
        else:
            safe_print("Invalid choice.")