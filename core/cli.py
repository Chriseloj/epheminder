from core.reminder_services import ReminderService
from core.user_services import UserService
from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from infrastructure.repositories import ReminderRepository
from core.exceptions import ReminderTextTooLongError, InvalidExpirationError, MaxRemindersReachedError, InvalidPasswordError, CLIExit
from infrastructure.storage import SessionLocal
from core.logout import logout as logout_service
from core.cli_utils import safe_print, safe_input, log_event
from core.decorators import require_login
from core.session import session_manager
import logging

logger = logging.getLogger(__name__)

# ------------------------------
# CLI Actions
# ------------------------------
def register_user(db_session):
    safe_print("\n=== Register ===")
    username = safe_input("Username: ")
    password = safe_input("Password: ")
    ip = "127.0.0.1"  # CLI local

    try:
        user = RegistrationService.register(
            username=username,
            password=password,
            ip=ip,
            db_session=db_session
        )
    except InvalidPasswordError as e:

        safe_print(f"Registration failed: {e}")

        log_event("warning", "register_failed", user_id=session_manager.current_user)
        return
    except Exception as e:
        safe_print(f"Registration failed: An unexpected error occurred: {e}")
        log_event("error", "register_failed", user_id=session_manager.current_user)
        return

    # If successful
    safe_print(f"User '{username}' registered successfully!")
    log_event("info", "register_success", user_id=session_manager.current_user)

def login_user(db_session):

    ip = "127.0.0.1"  # CLI local

    if session_manager.logged_in:
        safe_print("Already logged in. Please logout first.")
        log_event("warning", "login_failed",
                user_id=session_manager.current_user)
        return
    
    safe_print("=== Login ===")
    username = safe_input("Username: ")
    password = safe_input("Password: ")
   

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

        session_manager.set(
            user,
            access_token,
            refresh_token
        )
        safe_print("Login successful.")
        log_event("info", "login_success", user_id=session_manager.current_user)

    except AuthenticationRequiredError as e:
        safe_print(f"Login blocked or rate-limited: {e}")
        log_event("warning", "login_failed", user_id=session_manager.current_user)

    except Exception as e:
        safe_print(f"Login failed: {e}")
        log_event("warning", "login_failed", user_id=session_manager.current_user)
        
def create_reminder(db_session):

    ip = "127.0.0.1"  # CLI local

    safe_print("=== Create Reminder ===")
    text = safe_input("Reminder text: ")

    try:

        amount = int(safe_input("Expires in amount: "))

    except ValueError:

        safe_print("Expiration amount must be a number.")
        log_event("warning", "create_failed", user_id=session_manager.current_user)
        return
    
    unit = safe_input("Unit (minutes/hours/days): ")

    repo = ReminderRepository(db_session)

    try:

        reminder = ReminderService.create_reminder(
            user=session_manager.current_user,
            text=text,
            amount=amount,
            unit=unit,
            reminder_repo=repo
        )
        safe_print(f"Reminder created. ID: {reminder.id}")

    except ReminderTextTooLongError as e:
        safe_print(f"Reminder text too long (max {e.max_length} chars).")
        log_event("warning", "create_failed", user_id=session_manager.current_user)
    except MaxRemindersReachedError as e:
        safe_print(f"You have reached the maximum of {e.max_reminders_per_user} reminders.")
        log_event("warning", "create_failed", user_id=session_manager.current_user)
    except InvalidExpirationError as e:
        safe_print(f"Invalid expiration: {e}")
        log_event("warning", "create_failed", user_id=session_manager.current_user)
    except Exception as e:
        log_event("warning", "create_failed", user_id=session_manager.current_user)
        safe_print("Failed to create reminder. Please try again later.")

def list_reminders(db_session):
    ip = "127.0.0.1"  # CLI local
    safe_print("=== List Reminders ===")

    try:
        repo = ReminderRepository(db_session)
        reminders = ReminderService.list_reminders(session_manager.current_user, reminder_repo=repo)
        if not reminders:
            safe_print("No active reminders.")
            return
        for r in reminders:
            safe_print(f"- ID: {r.id} | Text: {r.text} | Expires: {r.expires_at}")
   
    except InvalidExpirationError as e:
        safe_print(f"Invalid expiration: {e}")
        log_event("warning", "list_failed", user_id=session_manager.current_user)
    except PermissionDeniedError:
        safe_print("Permission denied for listing reminders.")
        log_event("warning", "list_failed", user_id=session_manager.current_user)
    except Exception as e:
        log_event("warning", "list_failed", user_id=session_manager.current_user)
        safe_print("Failed to list reminder. Please check your input or try again later.")

def delete_reminder(db_session):
    ip = "127.0.0.1"  # CLI local
    safe_print("=== Delete Reminder ===")
    
    reminder_id = safe_input("Reminder ID: ")
    if isinstance(reminder_id, str) and reminder_id.isdigit():
        reminder_id = int(reminder_id)

    try:
        repo = ReminderRepository(db_session)
        success = ReminderService.delete_reminder(
            session_manager.current_user,
            reminder_id,
            reminder_repo=repo
        )

        if success:
            safe_print("Reminder deleted successfully.")
            log_event("info", "delete_success", user_id=session_manager.current_user)
        else:
            safe_print("Reminder not found.")
            log_event("warning", "delete_failed", user_id=session_manager.current_user)

    except PermissionDeniedError:
        safe_print("Permission denied for deleting reminders.")
        log_event("warning", "delete_failed", user_id=session_manager.current_user)
    except Exception:
        log_event("warning", "delete_failed", user_id=session_manager.current_user)
        safe_print("Failed to delete reminder. Please try again later.")

def logout(db_session):
    ip = "127.0.0.1"

    if not session_manager.logged_in:
        safe_print("You are not logged in.")
        log_event("warning", "logout_failed", user_id=session_manager.current_user)
        return

    user_id = getattr(session_manager.current_user, "id", None)

    try:
        logout_service(
            refresh_token=session_manager.refresh_token,
            access_token=session_manager.access_token,
            db_session=db_session
        )
    except Exception:
        log_event("warning", "logout_failed", user_id=session_manager.current_user)

    session_manager.clear()
    safe_print("Logged out successfully.")
    log_event("info", "logout_success", user_id=session_manager.current_user)

def exit_app():
    raise CLIExit()
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
    ip = "127.0.0.1"  # CLI local
    db_session = SessionLocal()

    try:
        while True:
            safe_print("\n" + "="*30)
            safe_print("      REMINDER APP CLI")
            safe_print("="*30)
            for k, (desc, _) in sorted(menu.items()):
                safe_print(f"{k}. {desc}")

            choice = safe_input("\nChoose an option: ")
            action = menu.get(choice)
            if action:
                safe_print("\n")
                action_func = action[1]

                # ------------------------------
                # Apply require_login dynamically at runtime
                # This avoids errors during pytest collection because db_session doesn't exist at import time.
                # Only wrap functions that need login.
                # ------------------------------
                if action_func in [create_reminder, list_reminders, delete_reminder]:
                    action_func = require_login(session_manager)(action_func)

                action_func(db_session=db_session)
            else:
                safe_print("Invalid choice. Try again.\n")
                log_event("warning", "run_failed", user_id=session_manager.current_user)

    except CLIExit:
        safe_print("Exiting.")

    finally:
        db_session.close()