import asyncio
import os
import json
import random
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === НАСТРОЙКА ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
SAVE_FILE = "kingdoms.json"
user_data = {}

# === МОДЕЛЬ КОРОЛЕВСТВА ===
class Kingdom:
    def __init__(self):
        self.resources = {"gold": 1000, "food": 500, "wood": 300, "iron": 200}
        self.army = {"infantry": 10, "archers": 5, "knights": 2}
        self.buildings = {"farms": 1, "mines": 1, "barracks": 1}
        self.level = 1
        self.exp = 0
        self.last_bonus = None  # для ежедневной награды

    def add_exp(self, amount):
        """Добавляет опыт и повышает уровень"""
        self.exp += amount
        needed = self.level * 100
        if self.exp >= needed:
            self.level += 1
            self.exp -= needed
            return True
        return False

# === ФУНКЦИИ ХРАНЕНИЯ ===
def save_data():
    data = {uid: k.__dict__ for uid, k in user_data.items()}
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for uid, kdata in data.items():
                k = Kingdom()
                k.__dict__.update(kdata)
                user_data[int(uid)] = k
        logger.info("Данные загружены.")

def get_or_create_kingdom(user_id):
    if user_id not in user_data:
        user_data[user_id] = Kingdom()
        save_data()
    return user_data[user_id]

# === МЕНЮ ===
MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("📊 Статус", callback_data="status")],
    [InlineKeyboardButton("⚔️ Атаковать", callback_data="attack")],
    [InlineKeyboardButton("🤺 PvP-битва", callback_data="pvp")],
    [InlineKeyboardButton("🏗 Развивать", callback_data="build")],
    [InlineKeyboardButton("🌾 Собрать ресурсы", callback_data="collect")],
    [InlineKeyboardButton("🎁 Ежедневная награда", callback_data="bonus")]
])

# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_kingdom(user_id)
    await update.message.reply_text(
        "👑 Добро пожаловать, Властелин!\n\nВыбери действие:",
        reply_markup=MAIN_MENU
    )

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)

    status_text = (
        f"*🏰 Королевство (Уровень {kingdom.level})*\n"
        f"📈 Опыт: {kingdom.exp}/{kingdom.level * 100}\n\n"
        f"*💎 Ресурсы:*\n"
        f"💰 Золото: {kingdom.resources['gold']}\n"
        f"🌾 Еда: {kingdom.resources['food']}\n"
        f"🪵 Дерево: {kingdom.resources['wood']}\n"
        f"⛓ Железо: {kingdom.resources['iron']}\n\n"
        f"*⚔️ Армия:*\n"
        f"🪖 Пехота: {kingdom.army['infantry']}\n"
        f"🏹 Лучники: {kingdom.army['archers']}\n"
        f"🛡 Рыцари: {kingdom.army['knights']}\n\n"
        f"*🏗 Здания:*\n"
        f"🌾 Фермы: {kingdom.buildings['farms']}\n"
        f"⛏ Шахты: {kingdom.buildings['mines']}\n"
        f"🏰 Казармы: {kingdom.buildings['barracks']}"
    )

    await query.edit_message_text(status_text, reply_markup=MAIN_MENU, parse_mode="Markdown")

# === АТАКИ ===
async def attack_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("⚔️ Слабый враг (50 золота)", callback_data="attack_weak")],
        [InlineKeyboardButton("🛡 Средний враг (150 золота)", callback_data="attack_medium")],
        [InlineKeyboardButton("🏰 Сильный враг (300 золота)", callback_data="attack_strong")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    gif = "https://media.giphy.com/media/XbxZ41fWLeRECPsGIJ/giphy.gif"
    await query.message.reply_animation(animation=gif, caption="⚔️ Воины собираются в поход...")
    await query.edit_message_text("Выбери противника:", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)
    attack_type = query.data

    data = {
        "attack_weak": {"cost": 50, "reward": {"gold": 100, "food": 50}, "exp": 30,
                        "gif": "https://media.giphy.com/media/5xaOcLT1D2RzD0WJwI0/giphy.gif"},
        "attack_medium": {"cost": 150, "reward": {"gold": 250, "food": 120}, "exp": 70,
                          "gif": "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"},
        "attack_strong": {"cost": 300, "reward": {"gold": 500, "food": 250}, "exp": 150,
                          "gif": "https://media.giphy.com/media/26tPplGWjN0xLybiU/giphy.gif"},
    }

    if kingdom.resources["gold"] < data[attack_type]["cost"]:
        await query.edit_message_text("❌ Недостаточно золота для атаки!", reply_markup=MAIN_MENU)
        return

    kingdom.resources["gold"] -= data[attack_type]["cost"]
    await query.message.reply_animation(animation=data[attack_type]["gif"], caption="⚔️ Сражение началось!")
    await asyncio.sleep(2)
    reward = data[attack_type]["reward"]
    kingdom.resources["gold"] += reward["gold"]
    kingdom.resources["food"] += reward["food"]
    leveled_up = kingdom.add_exp(data[attack_type]["exp"])
    save_data()

    result = (
        f"🎉 *Победа!*\n\n"
        f"💰 +{reward['gold']} золота\n"
        f"🌾 +{reward['food']} еды\n"
        f"📈 +{data[attack_type]['exp']} опыта"
    )
    if leveled_up:
        result += f"\n\n🆙 *Новый уровень: {kingdom.level}!*"
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=MAIN_MENU)

# === PvP ===
async def pvp_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    player = get_or_create_kingdom(user_id)

    if len(user_data) < 2:
        await query.edit_message_text("👀 Пока нет других игроков для битвы!", reply_markup=MAIN_MENU)
        return

    opponents = [uid for uid in user_data.keys() if uid != user_id]
    opponent_id = random.choice(opponents)
    enemy = get_or_create_kingdom(opponent_id)

    await query.message.reply_animation(
        animation="https://media.giphy.com/media/12XMGIWtrHBl5e/giphy.gif",
        caption="🤺 Рыцари встречаются на поле боя!"
    )
    await asyncio.sleep(2)

    winner = random.choice(["player", "enemy"])
    gold_stake = min(200, enemy.resources["gold"] // 2)

    if winner == "player":
        player.resources["gold"] += gold_stake
        player.add_exp(100)
        enemy.resources["gold"] -= gold_stake
        text = f"🏆 *Ты победил другого игрока!* 💰 +{gold_stake} золота, 📈 +100 опыта!"
    else:
        player.resources["gold"] = max(0, player.resources["gold"] - gold_stake)
        enemy.resources["gold"] += gold_stake
        text = f"💀 *Ты проиграл сражение...* Потеряно {gold_stake} золота."

    save_data()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=MAIN_MENU)

# === РАЗВИТИЕ ===
async def build_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🌾 Улучшить ферму (100 дерева)", callback_data="build_farm")],
        [InlineKeyboardButton("⛏ Улучшить шахту (150 дерева)", callback_data="build_mine")],
        [InlineKeyboardButton("🏰 Улучшить казарму (200 дерева)", callback_data="build_barracks")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    await query.edit_message_text("🏗 Что хочешь улучшить?", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)
    build_type = query.data
    costs = {
        "build_farm": {"wood": 100},
        "build_mine": {"wood": 150},
        "build_barracks": {"wood": 200}
    }
    if kingdom.resources["wood"] < costs[build_type]["wood"]:
        await query.edit_message_text("❌ Недостаточно дерева!", reply_markup=MAIN_MENU)
        return
    kingdom.resources["wood"] -= costs[build_type]["wood"]
    building_key = build_type.replace("build_", "") + "s"
    kingdom.buildings[building_key] += 1
    leveled_up = kingdom.add_exp(50)
    save_data()
    text = f"🏗 Улучшено: {building_key}! 📈 +50 опыта."
    if leveled_up:
        text += f"\n\n🆙 *Новый уровень: {kingdom.level}!*"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=MAIN_MENU)

# === СБОР РЕСУРСОВ ===
async def collect_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)
    food_collected = kingdom.buildings["farms"] * 60
    gold_collected = kingdom.buildings["mines"] * 40
    kingdom.resources["food"] += food_collected
    kingdom.resources["gold"] += gold_collected
    leveled_up = kingdom.add_exp(20)
    save_data()
    text = f"🌾 Собрано: +{food_collected} еды, +{gold_collected} золота. 📈 +20 опыта."
    if leveled_up:
        text += f"\n\n🆙 *Уровень {kingdom.level}!*"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=MAIN_MENU)

# === ЕЖЕДНЕВНАЯ НАГРАДА ===
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)
    today = datetime.date.today().isoformat()
    if kingdom.last_bonus == today:
        await query.edit_message_text("🎁 Ты уже получил награду сегодня! Возвращайся завтра!", reply_markup=MAIN_MENU)
        return
    bonus = {"gold": 200, "food": 150, "wood": 100, "iron": 50}
    for k, v in bonus.items():
        kingdom.resources[k] += v
    kingdom.last_bonus = today
    leveled_up = kingdom.add_exp(50)
    save_data()
    text = "🎉 *Ежедневная награда получена!*\n" + "\n".join([f"+{v} {k}" for k, v in bonus.items()]) + "\n📈 +50 опыта."
    if leveled_up:
        text += f"\n\n🆙 *Новый уровень: {kingdom.level}!*"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=MAIN_MENU)

# === ПРОЧЕЕ ===
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👑 Выбери действие:", reply_markup=MAIN_MENU)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

# === ЗАПУСК ===
def main():
    load_data()
    if not TOKEN:
        logger.error("❌ Токен не найден! Установи TELEGRAM_TOKEN.")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_status, pattern="^status$"))
    app.add_handler(CallbackQueryHandler(attack_menu, pattern="^attack$"))
    app.add_handler(CallbackQueryHandler(process_attack, pattern="^attack_"))
    app.add_handler(CallbackQueryHandler(build_menu, pattern="^build$"))
    app.add_handler(CallbackQueryHandler(process_build, pattern="^build_"))
    app.add_handler(CallbackQueryHandler(collect_resources, pattern="^collect$"))
    app.add_handler(CallbackQueryHandler(pvp_battle, pattern="^pvp$"))
    app.add_handler(CallbackQueryHandler(daily_bonus, pattern="^bonus$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back$"))
    app.add_error_handler(error_handler)
    logger.info("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
