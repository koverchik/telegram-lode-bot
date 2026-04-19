def group_by_letter(uslugi):
    result = {}

    for u in uslugi:
        name = u["name"].strip()
        letter = name[0].upper()

        if letter not in result:
            result[letter] = []

        result[letter].append(u)

    return result



from datetime import datetime

def format_ticket_time(iso_string):
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d.%m.%Y %H:%M")