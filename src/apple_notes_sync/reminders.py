"""AppleScript wrapper for Reminders.app."""

import subprocess


def _run(script: str) -> str:
    """Run AppleScript and return stdout."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "Reminders.app timeout (>30s). Try restarting Reminders."
        ) from None
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "not allowed" in stderr.lower():
            raise RuntimeError(
                "Automation permission required. "
                "Grant in System Settings > Privacy & Security > Automation."
            )
        raise RuntimeError(f"AppleScript error: {stderr}")
    return result.stdout.strip()


def create_list(name: str) -> None:
    """Create a reminders list if it doesn't exist."""
    _run(f'''
        tell application "Reminders"
            if not (exists list "{name}") then
                make new list with properties {{name:"{name}"}}
            end if
        end tell
    ''')


def list_reminders(list_name: str) -> list[dict]:
    """Get all reminders from a list. Returns [{id, name, body, completed}]."""
    raw = _run(f'''
        tell application "Reminders"
            if not (exists list "{list_name}") then return ""
            set output to ""
            repeat with r in (reminders of list "{list_name}")
                set rid to id of r
                set rname to name of r
                set rbody to body of r
                if rbody is missing value then set rbody to ""
                set rdone to completed of r
                set output to output & rid & "|||" & rname & "|||" & rbody & "|||" & rdone & linefeed
            end repeat
            return output
        end tell
    ''')
    if not raw:
        return []
    reminders = []
    for line in raw.strip().splitlines():
        parts = line.split("|||")
        if len(parts) < 4:
            continue
        reminders.append(
            {
                "id": parts[0],
                "name": parts[1],
                "body": parts[2],
                "completed": parts[3] == "true",
            }
        )
    return reminders


def create_reminder(list_name: str, name: str, body: str = "") -> str:
    """Create a reminder and return its ID."""
    esc_name = name.replace('"', '\\"')
    esc_body = body.replace('"', '\\"')
    return _run(f'''
        tell application "Reminders"
            set newReminder to make new reminder in list "{list_name}" with properties {{name:"{esc_name}", body:"{esc_body}"}}
            return id of newReminder
        end tell
    ''')


def set_completed(list_name: str, reminder_id: str, completed: bool) -> None:
    """Toggle completion state of a reminder."""
    val = "true" if completed else "false"
    _run(f'''
        tell application "Reminders"
            repeat with r in (reminders of list "{list_name}")
                if id of r is "{reminder_id}" then
                    set completed of r to {val}
                    exit repeat
                end if
            end repeat
        end tell
    ''')


def delete_reminder(list_name: str, reminder_id: str) -> None:
    """Delete a reminder by ID."""
    _run(f'''
        tell application "Reminders"
            repeat with r in (reminders of list "{list_name}")
                if id of r is "{reminder_id}" then
                    delete r
                    exit repeat
                end if
            end repeat
        end tell
    ''')
