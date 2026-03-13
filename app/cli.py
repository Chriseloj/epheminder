from application.auth_flow import register, login
from application.reminder_flow import create_reminder, list_reminders, delete_reminder
from application.session_services import SessionService

from cli.cli_exceptions import CLIExit
from cli.cli_utils import safe_print, safe_input, log_event

from infrastructure.storage import SessionLocal
from infrastructure.repositories import ReminderRepository

from core.registration import RegistrationService
from core.authentication_service import AuthenticationService
from core.user_services import UserService
from cli.cli_decorators import require_login
from core.session import session_manager as core_session_manager

import uuid


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
            return "Logged out successfully."
        else:
            return "You are not logged in."

    def exit_action(*_, **kwargs):
        raise CLIExit()

    # ------------------------------
    # Menu mapping
    # ------------------------------
    menu = {
        "1": ("Register", register),
        "2": ("Login", login),
        "3": ("Create Reminder", require_login(session_service)(create_reminder)),
        "4": ("List Reminders", require_login(session_service)(list_reminders)),
        "5": ("Delete Reminder", require_login(session_service)(delete_reminder)),
        "6": ("Logout", logout_action),
        "0": ("Exit", exit_action),
    }

    try:
        while True:
            # ------------------------------
            # Print Menu
            # ------------------------------
            safe_print("\n" + "=" * 30)
            safe_print("      Epheminder APP CLI")
            safe_print("=" * 30)

            for option, (description, _) in sorted(menu.items()):
                safe_print(f"{option}. {description}")

            choice = safe_input("\nChoose an option: ")
            action = menu.get(choice)

            if not action:
                safe_print("Invalid choice. Try again.\n")
                continue

            action_func = action[1]

            # ------------------------------
            # Collect arguments and execute
            # ------------------------------

            # logout / exit
            if action_func.__name__ == "exit_action":
                    
                action_func()
                continue

            else:

                try:

                    if action_func.__name__ == "register":
                        username = safe_input("Username: ")
                        password = safe_input("Password: ")
                        result = action_func(
                            username=username,
                            password=password,
                            db_session=db_session,
                            session_service=session_service,
                            registration_service=registration_service,
                        )

                    elif action_func.__name__ == "login":
                        username = safe_input("Username: ")
                        password = safe_input("Password: ")
                        result = action_func(
                            username=username,
                            password=password,
                            db_session=db_session,
                            session_service=session_service,
                            authentication_service=authentication_service,
                            user_service=user_service,
                        )

                    elif action_func.__name__ == "create_reminder":
    
                        if not session_service.logged_in:
                            safe_print("You must be logged in.")
                            continue

                        text = safe_input("Reminder text: ").strip()
                        if not text:
                            safe_print("Error: Reminder text cannot be empty.")
                            continue

                        amount_input = safe_input("Expiration amount: ").strip()
                        if not amount_input:
                            safe_print("Error: Expiration amount is required.")
                            continue

                        try:
                            amount = int(amount_input)
                        
                        except ValueError:
                            safe_print("Error: Expiration amount must be a number.")
                            continue

                        unit = safe_input("Expiration unit (minutes/hours/days): ").strip().lower()
                        if unit not in ["minutes", "hours", "days"]:
                            safe_print(f"Error: Invalid unit '{unit}'. Must be minutes, hours, or days.")
                            continue

                        result = action_func(
                            user=session_service.current_user,
                            text=text,
                            amount=amount,
                            unit=unit,
                            reminder_repo=reminder_repo,
                        )

                    elif action_func.__name__ == "list_reminders":
                        if not session_service.logged_in:
                            safe_print("You must be logged in.")
                            continue
                        result = action_func(
                            user=session_service.current_user,
                            reminder_repo=reminder_repo,
                        )

                    elif action_func.__name__ == "delete_reminder":

                        if not session_service.logged_in:
                            safe_print("You must be logged in.")
                            continue

                        # Show reminders before asking for ID
                        list_result = list_reminders(
                            user=session_service.current_user,
                            reminder_repo=reminder_repo,
                        )

                        if not list_result.get("success"):
                            safe_print(f"Error: {list_result.get('error')}")
                            continue

                        reminders = list_result.get("reminders", [])

                        if not reminders:
                            safe_print("No active reminders.")
                            continue

                        safe_print("\nYour reminders:\n")

                        reminders = sorted(reminders, key=lambda r: r["expires_at"])

                        for r in reminders:
                            safe_print(
                                f"- ID: {r['id']} | Text: {r['text']} | Expires: {r['expires_at']}"
                            )

                        reminder_id_input = safe_input("\nReminder ID to delete (ENTER to cancel): ").strip()

                        if not reminder_id_input:
                            safe_print("Cancelled.")
                            continue

                        try:
                             
                            reminder_id = str(uuid.UUID(reminder_id_input))
    
                        except ValueError:
                            safe_print("Invalid reminder ID format.")
                            continue

                        result = action_func(
                            user=session_service.current_user,
                            reminder_id=reminder_id,
                            reminder_repo=reminder_repo,
                        )

                    else:
            
                        result = action_func()

                except Exception as e:
                    result = {"success": False, "error": f"Action failed: {e}"}

            # ------------------------------
            # Present results
            # ------------------------------
            if isinstance(result, dict):
                if result.get("success"):
                    if "user" in result:
                        safe_print(f"Success: {result['user'].username}")
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

            elif result:
                safe_print(result)

    except CLIExit:
        safe_print("Exiting.")
    finally:
        db_session.close()