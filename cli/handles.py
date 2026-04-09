from application.auth_flow import register, login
from application.reminder_flow import create_reminder, list_reminders, delete_reminder

from cli.cli_utils import safe_print, safe_input, print_section, validate_unit, format_invalid_unit_message, normalize_time_unit
from core.tagger import Tagger
from core.exceptions import InvalidExpirationError

import uuid

"""
CLI handlers for user interaction.

This module acts as a thin layer between the CLI interface and the
application use cases (auth_flow, reminder_flow).

Responsibilities:
- Collect user input safely
- Perform minimal validation
- Call application services / use cases
- Return standardized response dictionaries

All handlers return a dict with at least:
    - success (bool)
    - error (str, optional)
    - additional data depending on the use case
"""

def print_reminders(reminders):
    """
    Imprime una lista de ReminderDB en CLI.
    """
    safe_print("\nYour reminders:\n")
    if not reminders:
        safe_print("No active reminders.")
        return

    for r in reminders:
        safe_print(format_reminder(r))

def _selected_print(reminders):
    if not reminders:
        safe_print("No active reminders.")
        return
    for r in reminders:
        safe_print(format_reminder(r))

def format_reminder(reminder):
    """
    Formats a reminder object for CLI display.

    Includes tags if available, otherwise displays basic reminder info.
    """

    tags = getattr(reminder, "tags", [])
    text = getattr(reminder, "text", "")
    expires = getattr(reminder, "expires_at", "N/A")
    rid = getattr(reminder, "id", "")

    if tags:
        tags_str = ', '.join(tags)
        return f"- Tags: {tags_str} | Text: {text} | Expires: {expires} | ID: {rid}"
    else:
        return f"- Text: {text} | Expires: {expires} | ID: {rid}"


def handle_register(session_service, registration_service, db_session):
    print_section("Register")

    username = safe_input("Username: ")
    password = safe_input("Password: ")

    return register(
        username=username,
        password=password,
        db_session=db_session,
        session_service=session_service,
        registration_service=registration_service,
    )


def handle_login(session_service, authentication_service, user_service, db_session):
    print_section("Login")

    username = safe_input("Username: ")
    password = safe_input("Password: ")

    result = login(
        username=username,
        password=password,
        db_session=db_session,
        session_service=session_service,
        authentication_service=authentication_service,
        user_service=user_service,
    )

    if not result.get("success"):
        return result
    
    user = result["user"]
    safe_print(f"Login successful! Welcome, {user.username}.\n") 

    return {
        "success": True,
        "data": user
    }

def handle_create_reminder(session_service, reminder_repo):
    """
    Handles user interaction for creating a reminder.

    Flow:
    - Collects and validates user input (text, expiration)
    - Generates suggested tags using the Tagger
    - Allows the user to accept or reject suggested tags
    - Calls the application layer to create the reminder
    - Displays the created reminder with optional tags

    Smart-tagging:
    - Tags are suggested automatically based on reminder text
    - Users can choose to accept or ignore them
    - Accepted tags are passed to the application layer

    Returns:
        dict: Standard CLI response with created reminder data
    """

    print_section("Create Reminder")

    # -----------------------------
    # Input 
    # -----------------------------
    text = safe_input("Reminder text: ").strip()
    if not text:
        return {"success": False, "error": "Reminder text cannot be empty."}

    amount_input = safe_input("Expiration amount: ").strip()
    if not amount_input:
        return {"success": False, "error": "Expiration amount is required."}
    try:
        amount = int(amount_input)
    except ValueError:
        return {"success": False, "error": "Expiration amount must be a number."}

    unit_input = safe_input("Expiration unit (m/h/d or minutes/hours/days): ").strip()
    unit_norm = normalize_time_unit(unit_input)  

    if not validate_unit(unit_norm):
        return {"success": False, "error": format_invalid_unit_message(unit_input)}

    # -----------------------------
    # Smart tagging optional
    # -----------------------------
    suggested_tags = Tagger.generate_tags(text)
    tags_to_use = []
    if suggested_tags:
        safe_print(f"Suggested tags: {', '.join(suggested_tags)}")
        answer = safe_input("Do you want to use these tags? (y/n): ").strip().lower()
        if answer == "y":
            tags_to_use = suggested_tags

    # -----------------------------
    # Create reminder
    # -----------------------------
    try:
        result = create_reminder(
            user=session_service.current_user,
            text=text,
            amount=amount,
            unit=unit_norm,  
            reminder_repo=reminder_repo,
            tags=tags_to_use
        )
    except InvalidExpirationError as e:
       
        return {"success": False, "error": str(e)}

    # -----------------------------
    # Show
    # -----------------------------
    if not result.get("success"):
        return result

    reminder_data = None

    if "reminder" in result:
        reminder_data = result["reminder"]
    elif "reminder_id" in result:
        reminder_data = {
            "id": result["reminder_id"],
            "text": text,
            "tags": tags_to_use
        }

    if reminder_data:
        if tags_to_use:  
            reminder_data["tags"] = tags_to_use
        else:  
            reminder_data["tags"] = [] 

    if reminder_data:
        reminder_str = f"- Text: {reminder_data['text']} | Expires: {reminder_data.get('expires_at', 'N/A')} | ID: {reminder_data['id']}"
        if reminder_data.get("tags"):
            reminder_str = f"- Tags: {', '.join(reminder_data['tags'])} | " + reminder_str[2:]
        safe_print("\nReminder created successfully:\n")
        safe_print(reminder_str + "\n")

        return {
            "success": True,
            "data": reminder_data
        }
    return {"success": False, "error": "Failed to create reminder."}

def handle_list_reminders(session_service, reminder_repo):
    print_section("List Reminders")

    result = list_reminders(
        user=session_service.current_user,
        reminder_repo=reminder_repo,
    )

    if not result.get("success"):
        return result

    reminders = result.get("reminders", [])

    if not reminders:
        safe_print("No active reminders.")
        return {"success": True, "data": []}

    for r in reminders:
        safe_print(format_reminder(r)) 

    return {"success": True, "data": reminders}

def handle_delete_reminder(session_service, reminder_repo):
    print_section("Delete Reminder")

    list_result = list_reminders(
        user=session_service.current_user,
        reminder_repo=reminder_repo,
    )

    if not list_result.get("success"):
        return list_result

    reminders = list_result.get("reminders", [])

    if not reminders:
        safe_print("No active reminders.")
        return {"success": True, "data": []}

    for r in reminders:
        safe_print(format_reminder(r))

    reminder_id_input = safe_input("\nReminder ID to delete (ENTER to cancel): ").strip()

    if not reminder_id_input:
        return {"success": True, "data": {"cancelled": True}}

    result = delete_reminder(
        user=session_service.current_user,
        reminder_id=reminder_id_input,
        reminder_repo=reminder_repo,
    )

    if result.get("success"):
        safe_print("\n✅ Reminder deleted successfully.")

    return result