import sys
from core.services import ReminderService, UserService
from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.security import Role, decode_token, hash_sensitive
from core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from infrastructure.repositories import ReminderRepository
from core.exceptions import ReminderTextTooLongError, InvalidExpirationError, MaxRemindersReachedError, InvalidPasswordError
from infrastructure.storage import SessionLocal
from core.logout import logout as logout_service
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# ------------------------------
# Session Management
# ------------------------------
current_token = None
current_user = None # cached user object
current_refresh_token = None
uid = current_user.id if current_user else None

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

def log_event(level, action, user_id=None, ip=None, extra_info=None):
    parts = [f"action={action}"]
    
    if user_id is not None:
        parts.append(f"user_hash={hash_sensitive(user_id)}")
    if ip is not None:
        parts.append(f"ip_hash={hash_sensitive(ip)}")
    if extra_info:
        parts.append(f"info={extra_info}")
    
    parts.append(f"ts={datetime.now(timezone.utc).isoformat()}")
    msg = " | ".join(parts)
    
    # Logging seguro solo al archivo
    if level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.debug(msg)

def safe_print(msg):
    print(msg)

def require_login(func):
    ip = "127.0.0.1"

    def wrapper(*args, **kwargs):
        db_session = kwargs.get("db_session")
        if not db_session:
            raise RuntimeError("db_session must be passed to CLI functions")

        global current_user

        if not current_token:
            safe_print("You must be logged in first.")
            log_event("warning", "login_failed", ip=ip)
            return

        try:
            payload = decode_token(current_token)
            user_id = payload["sub"]
            current_user = UserService.get_user_by_id(user_id, db_session=db_session)

        except AuthenticationRequiredError:
            safe_print("Authentication required. Please login again.")
            log_event("warning", "login_failed", ip=ip)
            clear_session()
            return

        except Exception:
            safe_print("Invalid token. Please login again.")
            log_event("warning", "login_failed", ip=ip)
            clear_session()
            return

        return func(*args, **kwargs)

    return wrapper
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

        log_event("warning", "register_failed", user_id=None, ip=ip)
        return
    except Exception as e:
        safe_print(f"Registration failed: An unexpected error occurred: {e}")
        log_event("error", "register_failed", user_id=None, ip=ip)
        return

    # If successful
    safe_print(f"User '{username}' registered successfully!")
    log_event("info", "register_success", user_id=user.id, ip=ip)

def login_user(db_session):

    ip = "127.0.0.1"  # CLI local

    if current_token:
        safe_print("Already logged in. Please logout first.")
        log_event("warning", "login_failed",user_id=current_user.id, ip=ip)
        return
    safe_print("=== Login ===")
    username = safe_input("Username: ")
    password = input("Password: ")
   

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
        log_event("info", "login_success", user_id=user.id, ip=ip)

    except AuthenticationRequiredError as e:
        safe_print(f"Login blocked or rate-limited: {e}")
        log_event("warning", "login_failed", user_id=getattr(current_user, "id", None), ip=ip)

    except Exception as e:
        safe_print(f"Login failed: {e}")
        log_event("warning", "login_failed", user_id=getattr(current_user, "id", None), ip=ip)
        
@require_login
def create_reminder(db_session):
    ip = "127.0.0.1"  # CLI local

    safe_print("=== Create Reminder ===")
    text = safe_input("Reminder text: ")
    try:
        amount = int(safe_input("Expires in amount: "))
    except ValueError:
        safe_print("Expiration amount must be a number.")
        log_event("warning", "create_failed",user_id=current_user.id, ip=ip)
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
        log_event("warning", "create_failed",user_id=current_user.id, ip=ip)
    except MaxRemindersReachedError as e:
        safe_print(f"You have reached the maximum of {e.max_reminders_per_user} reminders.")
        log_event("warning", "create_failed",user_id=current_user.id, ip=ip)
    except InvalidExpirationError as e:
        safe_print(f"Invalid expiration: {e}")
        log_event("warning", "create_failed",user_id=current_user.id, ip=ip)
    except Exception as e:
        log_event("warning", "create_failed",user_id=current_user.id, ip=ip)
        safe_print("Failed to create reminder. Please try again later.")

@require_login
def list_reminders(db_session):

    ip = "127.0.0.1"  # CLI local

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
        log_event("warning", "list_failed",user_id=current_user.id, ip=ip)
    except PermissionDeniedError:
        safe_print("Permission denied for listing reminders.")
        log_event("warning", "list_failed",user_id=current_user.id, ip=ip)
    except Exception as e:
        log_event("warning", "list_failed",user_id=current_user.id, ip=ip)  # stack trace to log
        safe_print("Failed to list reminder. Please check your input or try again later.")

@require_login
def delete_reminder(db_session):

    ip = "127.0.0.1"  # CLI local

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
            log_event("info", "delete_success",user_id=current_user.id, ip=ip)
            
        else:
            safe_print("Reminder not found.")
            log_event("warning", "delete_failed",user_id=current_user.id, ip=ip)

    except PermissionDeniedError:
        safe_print("Permission denied for deleting reminders.")
        log_event("warning", "delete_failed",user_id=current_user.id, ip=ip)
    except Exception:
        log_event("warning", "delete_failed",user_id=current_user.id, ip=ip)
        safe_print("Failed to delete reminder. Please try again later.")

def logout(db_session):
    ip = "127.0.0.1"  # CLI local
    global current_token, current_refresh_token

    user_id = getattr(current_user, "id", None)  # clear_session

    if not current_token:
        safe_print("You are not logged in.")
        log_event("warning", "logout_failed", user_id=user_id, ip=ip)
        return

    try:
        logout_service(
            refresh_token=current_refresh_token,
            access_token=current_token,
            db_session=db_session
        )
    except Exception:
        log_event("warning", "logout_failed", user_id=user_id, ip=ip)

    clear_session()
    safe_print("Logged out successfully.")
    log_event("info", "logout_success", user_id=user_id, ip=ip)

def exit_app():
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
                action[1](db_session=db_session)
            else:
                safe_print("Invalid choice. Try again.\n")
                log_event("warning", "run_failed",user_id=current_user.id, ip=ip)
    finally:
        db_session.close()