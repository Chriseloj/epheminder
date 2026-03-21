from application.session_services import SessionService

from cli.cli_exceptions import CLIExit
from cli.cli_utils import safe_print, safe_input, log_event
from cli.cli_decorators import require_login

from cli.handles import (
    handle_register,
    handle_login,
    handle_create_reminder,
    handle_list_reminders,
    handle_delete_reminder
)

from infrastructure.storage import SessionLocal
from infrastructure.repositories import ReminderRepository

from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.user_services import UserService
from core.session import session_manager as core_session_manager

from config import MENU_WIDTH


def run_cli():
    # ------------------------------
    # Dependencies (Composition Root)
    # ------------------------------
    db_session = SessionLocal()
    session_service = SessionService(session_manager=core_session_manager)
    reminder_repo = ReminderRepository(db_session)

    registration_service = RegistrationService
    authentication_service = AuthenticationService
    user_service = UserService

    # ------------------------------
    # Actions
    # ------------------------------
    def logout_action(*_, **kwargs):
        if session_service.logged_in:
            session_service.clear_session()
            log_event("info", "logout_success", user_id=None)
            return {"success": True, "message": "Logged out successfully."}

        return {"success": False, "error": "You are not logged in."}

    def exit_action(*_, **kwargs):
        raise CLIExit()

    # ------------------------------
    # Menu mapping
    # ------------------------------
    menu = {
        "1": ("Register", lambda: handle_register(session_service, registration_service, db_session)),
        "2": ("Login", lambda: handle_login(session_service, authentication_service, user_service, db_session)),
        "3": ("Create Reminder", require_login(session_service)(lambda: handle_create_reminder(session_service, reminder_repo))),
        "4": ("List Reminders", require_login(session_service)(lambda: handle_list_reminders(session_service, reminder_repo))),
        "5": ("Delete Reminder", require_login(session_service)(lambda: handle_delete_reminder(session_service, reminder_repo))),
        "6": ("Logout", logout_action),
        "0": ("Exit", exit_action),
    }

    try:
        while True:
            safe_print("\n" + "=" * MENU_WIDTH)
            safe_print("Epheminder".center(MENU_WIDTH))
            safe_print("=" * MENU_WIDTH)

            for option, (description, _) in sorted(menu.items()):
                safe_print(f"{option}. {description}")

            choice = safe_input("\nChoose an option: ")
            action = menu.get(choice)

            if not action:
                safe_print("Invalid choice. Try again.\n")
                continue

            action_func = action[1]

            try:
                result = action_func()
            except CLIExit:
                raise
            except Exception as e:
                log_event("error", "cli_action_failed", extra_info= str(e))
                result = {"success": False, "error":  e.public_message}

            if isinstance(result, dict):
                if result.get("success"):
                    if "user" in result:
                        safe_print(f"Success: {result['user'].username}")
                    elif result.get("cancelled"):
                        safe_print("Cancelled.")
                    elif "message" in result:
                        safe_print(result["message"])
                    elif "reminder_id" in result:
                        safe_print(f"Reminder created. ID: {result['reminder_id']}")
                    elif "reminders" in result:
                        reminders = result["reminders"]
                        if reminders:
                            for r in reminders:
                                safe_print(
                                    f"- ID: {r['id']} | Text: {r['text']} | Expires: {r['expires_at']}"
                                )
                        else:
                            safe_print("No active reminders.")
                    else:
                        safe_print("Action completed successfully.")
                else:
                    safe_print(f"Error: {result.get('error')}")

    except CLIExit:
        safe_print("Exiting.")
    finally:
        db_session.close()