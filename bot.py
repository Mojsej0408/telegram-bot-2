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
from PIL import Image




# === КОНФИГ ===
TG_TOKEN = '7648973124:AAGfrBkPu7T6FPSHnL_1g72Ph5tqor76PEw'
VK_TOKEN = 'vk1.a.MUz6b5M2fFq0gwLPT5-8YGj-BBgjv8iXWtSs9Y2fXLlvIXK5IQot7Y2TkgQOi94Zu0Iy49prjYNTR1wa9Tu60Fr1-T8J1_hEQgN6M1RPin5qYSSd8FSIeuzo43-00CYU6QZ8GTy7gsEhAQyAwI6JwygmR_3y3vCJztuV8A7BMk-CY9gdq4QzXIEvcLJamm7MJIV3Wa0oEzA6xSticp-kAg'

ADMIN_IDS = [5978354820]  # ЗАМЕНИ на свой Telegram ID
ADMIN_LOG_CHAT_ID = -1003847656490  # ID группы
ACTIVATION_FILE = 'activations.json'
MIN_DELAY = 300
EMOJIS = [
    "🔥", "🚀", "🎮", "💥", "⚡", "👾", "😎",
    "💎", "🧠", "📢", "✨", "🎯"
]
# === ПАГИНАЦИЯ ИГР ===
GAMES_PER_PAGE = 4




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
     },
    "Minecraft№2": {
        "Minecraft": -175474414,
        "Майн группа1": -63912735,
        "Майн группа2": -58088854,
        "Майн группа3": -76193574,
        "Майн группа4": -49056400
    },
    "Clash of Clans": {
        "Поиск клана в Clash of Clans!": -39134778,
        "Ищу клан/ Clash": -216593658,
        "Clash of Clans| пиар клана": -73830531,
        "клан в clash of clans": -76048544,
        "клеш Реклама кланов": -81811804
    }
}

user_state = {}
activated_users = {}

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
    for code, entry in data.items():
        if entry['user_id'] == user_id:
            expires = datetime.strptime(entry['expires_at'], "%Y-%m-%d")
            if datetime.now() <= expires:
                return True
    return False

def activate(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    args = context.args
    if not args:
        update.message.reply_text("⚠️ Введите код активации: /activate <код>")
        return

    code = args[0]
    data = load_activations()
    if code not in data:
        update.message.reply_text("❌ Код уже активирован или не найден.")
        return

    if data[code]['activated']:
        update.message.reply_text("⚠️ Этот код уже активирован.")
        return

    duration = data[code]['duration_days']
    expires = (datetime.now() + timedelta(days=duration)).strftime("%Y-%m-%d")

    data[code]['activated'] = True
    data[code]['user_id'] = user_id
    data[code]['expires_at'] = expires
    save_activations(data)
    log(context, f"🔑 АКТИВАЦИЯ\nID: {user_id}\nKEY: {code}")
    update.message.reply_text(f"✅ Активация успешна! Доступ до: {expires}")

def gen_code(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id not in ADMIN_IDS:
        update.message.reply_text("⛔ У тебя нет прав использовать эту команду.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        update.message.reply_text("⚠️ Используй: /gen_code <дней>")
        return

    days = int(args[0])
    code = generate_code(days)
    update.message.reply_text(f"✅ Код сгенерирован на {days} дней:\n🔑 <code>{code}</code>", parse_mode="HTML")

def require_activation(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_chat.id
        if not check_activation(user_id):
            context.bot.send_message(chat_id=user_id, text="🔒 Пожалуйста, активируйте доступ командой /activate <код>")
            return
        return func(update, context)
    return wrapper

def add_random_emoji(text: str) -> str:
    # шанс добавить эмодзи (80%)
    if random.random() < 0.95:
        return f"{text}\n\n{random.choice(EMOJIS)}"
    return text

def log(context, text):
    try:
        context.bot.send_message(ADMIN_LOG_CHAT_ID, text)
    except:
        pass

# === ОСНОВНОЙ ФУНКЦИОНАЛ ===
@require_activation
def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in user_state and user_state[user_id].get("is_running"):
        user_state[user_id]["is_running"] = False
        context.bot.send_message(chat_id=user_id, text="🛑 Предыдущий пиар остановлен.")

    user_state[user_id] = {
        "text": None,
        "game": None,
        "groups": [],
        "delay": None,
        "is_running": False
    }
    update.message.reply_text("Привет! Отправь мне текст для пиара.")
    log(context, f"▶️ START\nID: {user_id}")

@require_activation
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    if user_id not in user_state:
        update.message.reply_text("Сначала введи /start")
        return

    state = user_state[user_id]

    if state["text"] is None:
        state["text"] = update.message.text
        show_game_choice(update, context, 0)

    elif state["delay"] is None:
        try:
            delay = int(update.message.text)
            if delay < MIN_DELAY:
                update.message.reply_text(
                    f"⛔ Минимальная задержка — {MIN_DELAY} секунд.\n"
                    f"Введи значение не меньше {MIN_DELAY}."
                )
                return

            state["delay"] = delay
            show_launch_button(update, context)

        except ValueError:
            update.message.reply_text("Введи число для задержки в секундах.")
    else:
        update.message.reply_text("Пожалуйста, используй кнопки управления.")

@require_activation
def show_game_choice(update: Update, context: CallbackContext, page=0):
    user_id = update.effective_chat.id
    games = list(GAME_GROUPS.keys())

    start = page * GAMES_PER_PAGE
    end = start + GAMES_PER_PAGE
    page_games = games[start:end]

    keyboard = [
        [InlineKeyboardButton(f"🎮 {g}", callback_data=f"game_{g}")]
        for g in page_games
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"games_page_{page-1}")
        )
    if end < len(games):
        nav_buttons.append(
            InlineKeyboardButton("Вперёд ➡️", callback_data=f"games_page_{page+1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    if update.callback_query:
        update.callback_query.edit_message_text(
            text="Выбери игру для которой хочешь запустить пиар:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        context.bot.send_message(
            chat_id=user_id,
            text="Выбери игру для которой хочешь запустить пиар:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


@require_activation
def show_group_menu(update: Update, context: CallbackContext):
    user_id = update.callback_query.message.chat_id
    game = user_state[user_id]["game"]
    buttons = []
    for name, gid in GAME_GROUPS[game].items():
        selected = "✅" if gid in user_state[user_id]["groups"] else ""
        buttons.append([InlineKeyboardButton(f"{selected} {name}", callback_data=f"group_{gid}")])
    buttons.append([InlineKeyboardButton("✅ Выбрать все", callback_data="select_all")])
    buttons.append([InlineKeyboardButton("Далее ➡️", callback_data="next_delay")])
    context.bot.send_message(
        chat_id=user_id,
        text=f"Выбери группы в которую хочешь что бы бот постил твое сообщения ({game}):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@require_activation
def show_launch_button(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    keyboard = [[
        InlineKeyboardButton("🚀 Запустить пиар", callback_data="launch"),
        InlineKeyboardButton("🛑 Остановить пиар", callback_data="stop")
    ]]
    context.bot.send_message(
        chat_id=user_id,
        text=f"Текст и группы выбраны.\nЗадержка: {user_state[user_id]['delay']} сек.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@require_activation
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat_id
    data = query.data
    query.answer()
    state = user_state[user_id]
    if data.startswith("games_page_"):
        page = int(data.split("_")[-1])
        query.delete_message()
        show_game_choice(update, context, page)
        return


    if data.startswith("game_"):
        state["game"] = data.split("game_")[1]
        state["groups"] = []
        show_group_menu(update, context)
    elif data.startswith("group_"):
        gid = int(data.split("_")[1])
        if gid in state["groups"]:
            state["groups"].remove(gid)
        else:
            state["groups"].append(gid)
        show_group_menu(update, context)
    elif data == "select_all":
        state["groups"] = list(GAME_GROUPS[state["game"]].values())
        show_group_menu(update, context)
    elif data == "next_delay":
        if not state["groups"]:
            query.answer("❗ Выбери хотя бы одну группу.", show_alert=True)
            return
        query.edit_message_text(
    f"Теперь введи задержку в секундах перед запуском пиара:\n"
    f"⚠️ Минимальная задержка — {MIN_DELAY} секунд"
)
    elif data == "launch":
        if not state["text"] or not state["groups"] or state["delay"] is None:
            context.bot.send_message(chat_id=user_id, text="❗ Заполнены не все параметры.")
            return
        if state["is_running"]:
            context.bot.send_message(chat_id=user_id, text="⚠️ Пиар уже идёт.")
            return
        state["is_running"] = True
        context.bot.send_message(chat_id=user_id, text=f"🚀 Пиар каждые {state['delay']} сек.")
        log(context, f"🚀 START PIAR\nID: {user_id}\nDelay: {state['delay']}")
        threading.Thread(target=post_to_vk_loop, args=(user_id, context), daemon=True).start()
    elif data == "stop":
        state["is_running"] = False
        context.bot.send_message(chat_id=user_id, text="🛑 Пиар остановлен.")
        log(context, f"🛑 STOP PIAR\nID: {user_id}")

def post_to_vk_loop(user_id, context: CallbackContext):
    state = user_state[user_id]
    while state.get("is_running"):
        results = []
        for group_id in state["groups"]:
            try:
                final_text = add_random_emoji(state["text"])
                vk.wall.post(owner_id=group_id, message=final_text)
                results.append(f"✅ В группу {abs(group_id)}")
            except Exception as e:
                results.append(f"❌ Ошибка в {abs(group_id)}: {e}")
        context.bot.send_message(chat_id=user_id, text="\n".join(results))
        time.sleep(state["delay"])

def main():
    updater = Updater(TG_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("activate", activate))
    dp.add_handler(CommandHandler("gen_code", gen_code))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    updater.start_polling()
    print("Бот запущен")
    updater.idle()

if __name__ == '__main__':
    main()
