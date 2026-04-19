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
    usluga_id = int(parts[2])   # 👈 ВОТ ЭТО НОВОЕ

    data = load_all_data(usluga_id)  # 👈 ТЕПЕРЬ ПЕРЕДАЁШЬ

    tickets = data["tickets"]
    workers = {w["id"]: w for w in data["workers"]}
    branchs = {b["id"]: b for b in data["branchs"]}

    # фильтр врача
    if doctor_id != "all":
        tickets = [t for t in tickets if t["worker_id"] == int(doctor_id)]

    text = ""

    for t in tickets[:30]:
        worker = workers.get(t["worker_id"])
        branch = branchs.get(t["branch"])

        if not worker:
            continue

        name = f"{worker['surname']} {worker['name']} {worker['father']}"
        time = format_ticket_time(t["start"])
        address = branch["name"] if branch else "?????"

        text += f"👨‍⚕️ {name}\n"
        text += f"\n"
        text += f"🗓 {time}\n"
        text += f"\n"
        text += f"🏥 {address}\n"
        text += "──────────────\n"

    await callback.message.answer(text or "Нет талонов")

if __name__ == "__main__":
    asyncio.run(main())