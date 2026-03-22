from application.auth_flow import register, login
from application.reminder_flow import create_reminder, list_reminders, delete_reminder

from cli.cli_utils import safe_print, safe_input, print_section, normalize_time_unit

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

    return login(
        username=username,
        password=password,
        db_session=db_session,
        session_service=session_service,
        authentication_service=authentication_service,
        user_service=user_service,
    )


def handle_create_reminder(session_service, reminder_repo):
    """
    Handles CLI flow for creating a reminder.

    Requires an authenticated user.
    Performs input validation and normalizes time units.

    Returns:
        dict: Standard response with success/error.
    """
    print_section("Create Reminder")

    if not getattr(session_service, "current_user", None):
        return {"success": False, "error": "Authentication required."}

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

    unit = normalize_time_unit(
        safe_input("Expiration unit (m/h/d or minutes/hours/days): ").lower()
    )

    try:
        return create_reminder(
            user=session_service.current_user,
            text=text,
            amount=amount,
            unit=unit,
            reminder_repo=reminder_repo,
        )
    except InvalidExpirationError:
        return {"success": False, "error": "Invalid expiration value."}


def handle_list_reminders(session_service, reminder_repo):
    print_section("List Reminders")

    if not getattr(session_service, "current_user", None):
        return {"success": False, "error": "Authentication required."}

    return list_reminders(
        user=session_service.current_user,
        reminder_repo=reminder_repo,
    )


def handle_delete_reminder(session_service, reminder_repo):
    """
    Handles CLI flow for deleting a reminder.

    - Requires authentication
    - Displays reminders sorted by expiration
    - Allows user to cancel operation
    - Validates UUID format before deletion

    Returns:
        dict: Standard response with success/error.
    """
    print_section("Delete Reminder")

    if not getattr(session_service, "current_user", None):
        return {"success": False, "error": "Authentication required."}

    list_result = list_reminders(
        user=session_service.current_user,
        reminder_repo=reminder_repo,
    )

    if not list_result.get("success"):
        return list_result

    reminders = list_result.get("reminders", [])

    if not reminders:
        return {"success": True, "reminders": []}

    safe_print("\nYour reminders:\n")

    reminders = sorted(reminders, key=lambda r: r["expires_at"])

    for r in reminders:
        safe_print(
            f"- ID: {r['id']} | Text: {r['text']} | Expires: {r['expires_at']}"
        )

    reminder_id_input = safe_input("\nReminder ID to delete (ENTER to cancel): ").strip()

    if not reminder_id_input:
        return {"success": True, "cancelled": True}

    try:
        reminder_id = str(uuid.UUID(reminder_id_input))
    except ValueError:
        return {"success": False, "error": "Invalid reminder ID format."}

    return delete_reminder(
        user=session_service.current_user,
        reminder_id=reminder_id,
        reminder_repo=reminder_repo,
    )