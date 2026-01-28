from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import vk_api
import threading
import time
import json
import os
import random
import string
from datetime import datetime, timedelta

# === КОНФИГ ===
TG_TOKEN = '7648973124:AAGfrBkPu7T6FPSHnL_1g72Ph5tqor76PEw'
VK_TOKEN = 'vk1.a.MUz6b5M2fFq0gwLPT5-8YGj-BBgjv8iXWtSs9Y2fXLlvIXK5IQot7Y2TkgQOi94Zu0Iy49prjYNTR1wa9Tu60Fr1-T8J1_hEQgN6M1RPin5qYSSd8FSIeuzo43-00CYU6QZ8GTy7gsEhAQyAwI6JwygmR_3y3vCJztuV8A7BMk-CY9gdq4QzXIEvcLJamm7MJIV3Wa0oEzA6xSticp-kAg'

ADMIN_IDS = [5978354820]
ACTIVATION_FILE = 'activations.json'
MIN_DELAY = 300  # минимальная задержка

# === ГРУППЫ ===
GAME_GROUPS = {
    "SAMP": {
        "rus_samp": -42590964,
        "Minecraft-SAMP": -175474414,
        "Самп - Samp": -35298905,
        "САМП ПИАР": -224140658
    },
    "CS": {
        "Пиар CS-Go": -58921523,
        "Мониторинг CS CSS CS:GO": -208397664,
        "CS GO|CS 1.6|CSS V34|ПИАР": -38938816,
        "ПИАР СЕРВЕРОВ CS": -167982194
    },
    "Rust": {
        "RUST сервера": -42452760,
        "RUST | Пиар Серверов": -189208041,
        "Пиар RUST": -63469938
    },
    "Minecraft": {
        "Майнкрафт сервера": -60316425,
        "реклама серверов": -166922832,
        "реклама ": -226229313,
        "|Пиар|Реклама|": -116539840,
        "Minecraft - Samp": -79701815,
        "Майнкрафт|Пиар": -102372708
    },
    "Standoff 2": {
        "КЛАН/ТУРНИРЫ/КВ/МИКСЫ": -185186597,
        "Найти клан| Забить КВ": -165745863,
        "поиск кланов и кв": -172720565
    }
}

user_state = {}

# === VK API ===
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

# === АКТИВАЦИЯ ===
def load_activations():
    if os.path.exists(ACTIVATION_FILE):
        with open(ACTIVATION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_activations(data):
    with open(ACTIVATION_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def generate_code(duration_days):
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    data = load_activations()
    data[code] = {
        'activated': False,
        'user_id': None,
        'expires_at': None,
        'duration_days': duration_days
    }
    save_activations(data)
    return code

def check_activation(user_id):
    data = load_activations()
    for entry in data.values():
        if entry['user_id'] == user_id:
            expires = datetime.strptime(entry['expires_at'], "%Y-%m-%d")
            return datetime.now() <= expires
    return False

def notify_admin(text, context):
    for admin_id in ADMIN_IDS:
        context.bot.send_message(chat_id=admin_id, text=text)

def activate(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    args = context.args

    if not args:
        update.message.reply_text("⚠️ Используй: /activate <код>")
        return

    code = args[0]
    data = load_activations()

    if code not in data or data[code]['activated']:
        update.message.reply_text("❌ Код недействителен.")
        return

    expires = (datetime.now() + timedelta(days=data[code]['duration_days'])).strftime("%Y-%m-%d")
    data[code].update({
        'activated': True,
        'user_id': user_id,
        'expires_at': expires
    })
    save_activations(data)

    update.message.reply_text(f"✅ Доступ активирован до {expires}")
    notify_admin(f"🔑 Активация ключа\n👤 ID: {user_id}\n📅 До: {expires}", context)

def gen_code(update: Update, context: CallbackContext):
    if update.message.chat_id not in ADMIN_IDS:
        return
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text("Используй: /gen_code <дней>")
        return
    days = int(context.args[0])
    code = generate_code(days)
    update.message.reply_text(f"🔑 Код на {days} дней:\n<code>{code}</code>", parse_mode="HTML")

def require_activation(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_chat.id
        if not check_activation(user_id):
            context.bot.send_message(chat_id=user_id, text="🔒 Активируйте доступ: /activate <код>")
            return
        return func(update, context)
    return wrapper

@require_activation
def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_state[user_id] = {
        "text": None,
        "game": None,
        "groups": [],
        "delay": None,
        "is_running": False
    }
    update.message.reply_text("Привет! Отправь текст для пиара.")

@require_activation
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    state = user_state[user_id]

    if state["text"] is None:
        state["text"] = update.message.text
        show_game_choice(update, context)

    elif state["delay"] is None:
        try:
            delay = int(update.message.text)
            if delay < MIN_DELAY:
                raise ValueError
            state["delay"] = delay
            show_launch_button(update, context)
        except ValueError:
            update.message.reply_text(
                f"⛔ Минимальная задержка — {MIN_DELAY} секунд.\nВведи корректное значение."
            )

@require_activation
def show_game_choice(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton(f"🎮 {g}", callback_data=f"game_{g}")]
                for g in GAME_GROUPS]
    update.message.reply_text(
        "Выбери игру для пиара:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@require_activation
def show_group_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat_id
    game = user_state[user_id]["game"]

    buttons = []
    for name, gid in GAME_GROUPS[game].items():
        mark = "✅" if gid in user_state[user_id]["groups"] else ""
        buttons.append([InlineKeyboardButton(f"{mark} {name}", callback_data=f"group_{gid}")])

    buttons.append([InlineKeyboardButton("Далее ➡️", callback_data="next_delay")])

    query.edit_message_text(
        f"Выбери группы ({game}):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@require_activation
def show_launch_button(update: Update, context: CallbackContext):
    keyboard = [[
        InlineKeyboardButton("🚀 Запустить пиар", callback_data="launch"),
        InlineKeyboardButton("🛑 Остановить", callback_data="stop")
    ]]
    update.message.reply_text(
        f"Задержка установлена: {user_state[update.message.chat_id]['delay']} сек",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@require_activation
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat_id
    state = user_state[user_id]
    data = query.data
    query.answer()

    if data.startswith("game_"):
        state["game"] = data.replace("game_", "")
        state["groups"] = []
        show_group_menu(update, context)

    elif data.startswith("group_"):
        gid = int(data.split("_")[1])
        if gid in state["groups"]:
            state["groups"].remove(gid)
        else:
            state["groups"].append(gid)
        show_group_menu(update, context)

    elif data == "next_delay":
        query.message.reply_text(
            f"Теперь введи задержку в секундах.\n"
            f"⚠️ Минимальная задержка — {MIN_DELAY} секунд"
        )

    elif data == "launch":
        if not state["groups"] or not state["text"] or not state["delay"]:
            return
        state["is_running"] = True
        notify_admin(
            f"🚀 Запуск пиара\n👤 ID: {user_id}\n⏱ Задержка: {state['delay']} сек",
            context
        )
        threading.Thread(target=post_loop, args=(user_id, context), daemon=True).start()

    elif data == "stop":
        state["is_running"] = False
        query.message.reply_text("🛑 Пиар остановлен.")

def post_loop(user_id, context):
    state = user_state[user_id]
    while state["is_running"]:
        for gid in state["groups"]:
            try:
                vk.wall.post(owner_id=gid, message=state["text"])
            except:
                pass
        time.sleep(state["delay"])

def notify_restart(update: Update, context: CallbackContext):
    if update.message.chat_id not in ADMIN_IDS:
        return
    data = load_activations()
    for entry in data.values():
        if entry.get("user_id"):
            context.bot.send_message(
                chat_id=entry["user_id"],
                text="⚠️ Бот будет перезагружен в течение 5 минут. Ожидайте."
            )

def main():
    updater = Updater(TG_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("activate", activate))
    dp.add_handler(CommandHandler("gen_code", gen_code))
    dp.add_handler(CommandHandler("notify_restart", notify_restart))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    print("Бот запущен")
    updater.idle()

if __name__ == "__main__":
    main()
