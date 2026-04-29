import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import API_TOKEN
from api import load_uslugi, load_all_data, load_workers_data
from utils import group_by_letter, format_ticket_time

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA = {}

# --- START ---
@dp.message(F.text == "/start")
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Взрослый", callback_data="age:adult"),
            InlineKeyboardButton(text="Ребенок", callback_data="age:child")
        ]
    ])

    await message.answer("Выберите возраст:", reply_markup=kb)

@dp.callback_query(F.data.startswith("age"))
async def choose_age(callback: CallbackQuery):
    uslugi = load_uslugi()
    grouped = group_by_letter(uslugi)

    DATA["grouped"] = grouped

    buttons = []
    row = []

    for i, letter in enumerate(sorted(grouped.keys()), 1):
        row.append(InlineKeyboardButton(text=letter, callback_data=f"letter:{letter}"))

        if i % 6 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer("Выберите букву:", reply_markup=kb)

@dp.callback_query(F.data.startswith("letter"))
async def choose_letter(callback: CallbackQuery):
    letter = callback.data.split(":")[1]

    grouped = DATA.get("grouped", {})
    uslugi_list = grouped.get(letter, [])

    buttons = [
        [InlineKeyboardButton(text=u["name"], callback_data=f"usluga:{u['id']}")]
        for u in uslugi_list
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(
        f"Направления на букву {letter}:",
        reply_markup=kb
    )

async def main():
    await dp.start_polling(bot)

def get_workers_by_usluga(workers, usluga_id):
    result = []

    for w in workers:
        for u in w.get("uslugi", []):
            if u["id"] == usluga_id:
                result.append(w)
                break

    return result

@dp.callback_query(F.data.startswith("usluga"))
async def choose_usluga(callback: CallbackQuery):
    usluga_id = int(callback.data.split(":")[1])

    workers = load_workers_data(usluga_id)

    doctors = get_workers_by_usluga(workers, usluga_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    for d in doctors:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{d['surname']} {d['name']}",
                callback_data=f"doctor:{d['id']}:{usluga_id}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="Все врачи",
            callback_data=f"doctor:all:{usluga_id}"
        )
    ])

    await callback.message.answer("Выберите врача:", reply_markup=kb)

@dp.callback_query(F.data.startswith("doctor"))
async def choose_doctor(callback: CallbackQuery):
    parts = callback.data.split(":")

    doctor_id = parts[1]
    usluga_id = int(parts[2])

    data = load_all_data(usluga_id)

    tickets = data.get("tickets", [])
    workers = {w["id"]: w for w in data.get("workers", [])}
    branchs = {b["id"]: b for b in data.get("branchs", [])}

    # фильтр по врачу
    if doctor_id != "all":
        tickets = [t for t in tickets if t["worker_id"] == int(doctor_id)]

    # ❌ НЕТ ТАЛОНОВ → ПОКАЗЫВАЕМ КНОПКУ
    if not tickets:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔔 Сообщить о появлении",
                    callback_data=f"subscribe:{doctor_id}:{usluga_id}"
                )
            ]
        ])

        await callback.message.answer(
            "❌ Сейчас талонов нет\n\n"
            "Нажми кнопку, и я сообщу, когда появятся 👇",
            reply_markup=kb
        )
        return

    grouped = {}

    for t in tickets:
        wid = t["worker_id"]
        grouped.setdefault(wid, []).append(t)

    for wid, doctor_tickets in grouped.items():
        worker = workers.get(wid)

        if not worker:
            continue

        name = f"{worker['surname']} {worker['name']} {worker['father']}"

        text = f"🧑‍⚕️ {name}\n\n"

        for t in doctor_tickets[:10]:
            branch = branchs.get(t["branch"])
            time = format_ticket_time(t["start"])
            address = branch["name"] if branch else "???"

            text += f"🗓 {time}\n"
            text += f"🏥 {address}\n\n"

        await callback.message.answer(text)

SUBSCRIPTIONS = []

@dp.callback_query(F.data.startswith("subscribe"))
async def subscribe(callback: CallbackQuery):
    parts = callback.data.split(":")

    doctor_id = parts[1]
    usluga_id = int(parts[2])

    SUBSCRIPTIONS.append({
        "user_id": callback.from_user.id,
        "usluga_id": usluga_id,
        "doctor_id": doctor_id,
        "last_seen": set()
    })

    await callback.message.answer("✅ Подписка оформлена")

async def watcher():
    while True:
        print("checking subscriptions...")

        for sub in SUBSCRIPTIONS:
            data = load_all_data(sub["usluga_id"])

            tickets = data.get("tickets", [])

            if sub["doctor_id"] != "all":
                tickets = [
                    t for t in tickets
                    if t["worker_id"] == int(sub["doctor_id"])
                ]

            current_ids = {t["id"] for t in tickets}

            new_ids = current_ids - sub["last_seen"]

            if new_ids:
                sub["last_seen"] = current_ids

                for t in tickets:
                    if t["id"] in new_ids:
                        await bot.send_message(
                            sub["user_id"],
                            f"🎉 Новый талон!\n{t['start']}"
                        )

        await asyncio.sleep(600)

if __name__ == "__main__":
    asyncio.run(main())