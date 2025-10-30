from plyer import notification
def notify(title, message):
    try:
        notification.notify(title=title, message=message, timeout=4)
    except Exception:
        print("[NOTIFY]", title, message)
