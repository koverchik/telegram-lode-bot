import requests
from datetime import datetime, timezone, timedelta

URL_WITHOUT_TICKETS = "https://lz-lode.lode.by/getAllDataWithoutTickets"
URL_ALL = "https://lz-lode.lode.by/getAllData"

now = datetime.now(timezone.utc)

start = now.replace(hour=0, minute=0, second=0, microsecond=0)
end = now + timedelta(days=30)

start_iso = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
end_iso = end.strftime("%Y-%m-%dT%H:%M:%S.000Z")

# =========================
# SAFE REQUEST
# =========================
def safe_get(url, params):
    try:
        response = requests.get(url, params=params, timeout=10)

        print("STATUS:", response.status_code)

        if response.status_code != 200:
            print("ERROR TEXT:", response.text[:200])
            return {}

        return response.json()

    except Exception as e:
        print("REQUEST FAILED:", e)
        return {}


# =========================
# USLUGI
# =========================
def load_uslugi():
    data = safe_get(URL_WITHOUT_TICKETS, {
        "start": start_iso,
        "end": end_iso
    })

    return data.get("uslugi", [])


# =========================
# TICKETS BY USLUGA
# =========================
def load_tickets(usluga_id):

    data = safe_get(URL_ALL, {
        "start": start_iso,
        "end": end_iso,
        "usluga": usluga_id
    })

    return data.get("tickets", [])


# =========================
# FULL DATA
# =========================
def load_all_data(usluga_id):
    return safe_get(URL_ALL, {
        "start": start_iso,
        "end": end_iso,
        "usluga": usluga_id
    })

# =========================
# WORKERS DATA
# =========================
def load_workers_data(usluga_id):
    data = safe_get(URL_ALL, {
        "start": start_iso,
        "end": end_iso,
        "usluga": usluga_id
    })

    return data.get("workers", [])