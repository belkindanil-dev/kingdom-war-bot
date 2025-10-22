import random
import asyncio
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()

if not TOKEN:
    logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables")
    exit(1)

# --- База данных игроков ---
players = {}
active_duels = {}
pending_invites = {}
daily_quests = {}

class Player:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.level = 1
        self.exp = 0
        self.crystals = 100  # Стартовые кристаллы
        self.wins = 0
        self.losses = 0
        self.rating = 1000  # Рейтинговые очки
        self.sticker_sets = ["basic"]  # Начальный набор
        self.unlocked_stickers = {
            "basic": ["fireball", "icewall", "heal"],
            "lightning": [],
            "dark": [],
            "nature": []
        }
        self.daily_quests_completed = 0
        self.last_daily_quest = None
        self.quest_progress = {}

class Duel:
    def __init__(self, player1_id, player2_id, ranked=False):
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.player1_hp = 10
        self.player2_hp = 10
        self.player1_choice = None
        self.player2_choice = None
        self.round = 1
        self.started_at = datetime.now()
        self.ranked = ranked  # Рейтинговая ли дуэль

# --- Стикеры-заклинания ---
STICKERS = {
    "fireball": {
        "name": "🔥 Огненный шар",
        "type": "attack",
        "power": 3,
        "description": "Наносит 3 ед. урона",
        "set": "basic",
        "cost": 0
    },
    "icewall": {
        "name": "❄️ Ледяная стена", 
        "type": "defense",
        "power": 2,
        "counter_damage": 1,
        "description": "Блокирует 2 урона, наносит 1 отраженный урон",
        "set": "basic",
        "cost": 0
    },
    "heal": {
        "name": "💚 Целитель",
        "type": "heal",
        "power": 2,
        "description": "Восстанавливает 2 HP",
        "set": "basic",
        "cost": 0
    },
    "lightning": {
        "name": "⚡ Удар молнии",
        "type": "attack",
        "power": 4,
        "miss_chance": 0.2,
        "description": "Наносит 4 урона, но может промахнуться",
        "set": "lightning",
        "cost": 200
    },
    "thunder_shield": {
        "name": "🛡️ Громовой щит",
        "type": "defense", 
        "power": 999,
        "stun": True,
        "cooldown": 3,
        "description": "Блокирует весь урон и оглушает противника",
        "set": "lightning",
        "cost": 300
    },
    "curse": {
        "name": "👁️ Сглаз",
        "type": "curse",
        "power": 1,
        "duration": 2,
        "description": "Накладывает проклятие на 2 хода (1 урон/ход)",
        "set": "dark",
        "cost": 250
    },
    "soul_steal": {
        "name": "🖤 Похищение души",
        "type": "attack",
        "power": 2,
        "heal": 2,
        "description": "Ворует 2 HP у противника и добавляет к своим",
        "set": "dark",
        "cost": 350
    },
    "poison": {
        "name": "🐍 Ядовитое жало",
        "type": "poison",
        "power": 1,
        "duration": 3,
        "description": "Накладывает яд на 3 хода (1 урон/ход)",
        "set": "nature",
        "cost": 200
    },
    "healing_aura": {
        "name": "🌿 Исцеляющая аура",
        "type": "heal",
        "power": 3,
        "cleanse": True,
        "description": "Снимает негативные эффекты и восстанавливает 3 HP",
        "set": "nature",
        "cost": 300
    }
}

# --- Наборы стикеров ---
STICKER_SETS = {
    "lightning": {
        "name": "⚡ Набор Молнии",
        "cost": 500,
        "stickers": ["lightning", "thunder_shield"]
    },
    "dark": {
        "name": "🌑 Набор Тьмы", 
        "cost": 600,
        "stickers": ["curse", "soul_steal"]
    },
    "nature": {
        "name": "🌿 Набор Природы",
        "cost": 550,
        "stickers": ["poison", "healing_aura"]
    }
}

# --- Ежедневные задания ---
DAILY_QUESTS = [
    {
        "id": "win_3",
        "name": "🎯 Победи 3 раза",
        "description": "Одолей 3 противников в любых дуэлях",
        "target": 3,
        "reward": 50
    },
    {
        "id": "use_fireball",
        "name": "🔥 Мастер огня",
        "description": "Используй Огненный шар 5 раз",
        "target": 5,
        "reward": 30
    },
    {
        "id": "win_ranked",
        "name": "👑 Победа в рейтинге",
        "description": "Выиграй 2 рейтинговые дуэли",
        "target": 2,
        "reward": 70
    },
    {
        "id": "use_heal",
        "name": "💚 Исцелитель",
        "description": "Восстанови 10 HP с помощью лечения",
        "target": 10,
        "reward": 40
    }
]

def get_or_create_player(user_id, username):
    if user_id not in players:
        players[user_id] = Player(user_id, username)
        # Выдаем случайное ежедневное задание
        assign_daily_quest(user_id)
    return players[user_id]

def assign_daily_quest(user_id):
    """Выдает случайное ежедневное задание"""
    if user_id not in daily_quests:
        quest = random.choice(DAILY_QUESTS)
        daily_quests[user_id] = {
            "quest": quest,
            "progress": 0,
            "assigned_date": datetime.now().date()
        }

# --- Главное меню ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("⚔️ Найти дуэль", callback_data='find_duel'),
         InlineKeyboardButton("👑 Рейтинговая дуэль", callback_data='find_ranked')],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data='invite_friend')],
        [InlineKeyboardButton("📊 Мой профиль", callback_data='profile')],
        [InlineKeyboardButton("🏪 Магазин", callback_data='shop'),
         InlineKeyboardButton("🎯 Ежедневные задания", callback_data='quests')],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Меню выбора стикера ---
def sticker_menu(player_id):
    player = players[player_id]
    available_stickers = []
    
    for sticker_id, sticker in STICKERS.items():
        if sticker["set"] in player.sticker_sets:
            available_stickers.append(sticker_id)
    
    # Выбираем 3 случайных стикера
    selected_stickers = random.sample(available_stickers, min(3, len(available_stickers)))
    
    buttons = []
    for sticker_id in selected_stickers:
        sticker = STICKERS[sticker_id]
        buttons.append([InlineKeyboardButton(sticker["name"], callback_data=f'sticker_{sticker_id}')])
    
    return InlineKeyboardMarkup(buttons)

# --- Меню магазина ---
def shop_menu(player_id):
    player = players[player_id]
    buttons = []
    
    # Наборы стикеров
    for set_id, sticker_set in STICKER_SETS.items():
        if set_id not in player.sticker_sets:
            buttons.append([
                InlineKeyboardButton(
                    f"{sticker_set['name']} - {sticker_set['cost']}💎", 
                    callback_data=f'buy_set_{set_id}'
                )
            ])
    
    # Отдельные стикеры
    for sticker_id, sticker in STICKERS.items():
        if sticker["cost"] > 0 and sticker_id not in player.unlocked_stickers[sticker["set"]]:
            buttons.append([
                InlineKeyboardButton(
                    f"{sticker['name']} - {sticker['cost']}💎", 
                    callback_data=f'buy_sticker_{sticker_id}'
                )
            ])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])
    return InlineKeyboardMarkup(buttons)

# --- Меню ежедневных заданий ---
def quests_menu(player_id):
    player = players[player_id]
    quest_info = daily_quests.get(player_id)
    
    if not quest_info:
        assign_daily_quest(player_id)
        quest_info = daily_quests[player_id]
    
    quest = quest_info["quest"]
    progress = quest_info["progress"]
    
    quest_text = (
        f"🎯 **Твое задание:** {quest['name']}\n"
        f"📝 {quest['description']}\n"
        f"📊 Прогресс: {progress}/{quest['target']}\n"
        f"🎁 Награда: {quest['reward']}💎\n\n"
    )
    
    buttons = [[InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]]
    
    if progress >= quest['target']:
        buttons.insert(0, [InlineKeyboardButton("🎁 Получить награду", callback_data='claim_quest')])
    
    return quest_text, InlineKeyboardMarkup(buttons)

# --- Таблица лидеров ---
def get_leaderboard():
    sorted_players = sorted(players.values(), key=lambda x: x.rating, reverse=True)[:10]
    
    leaderboard_text = "🏆 **Топ 10 игроков:**\n\n"
    for i, player in enumerate(sorted_players, 1):
        leaderboard_text += f"{i}. {player.username} - {player.rating}⭐ (Ур. {player.level})\n"
    
    return leaderboard_text

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Игрок"
    
    player = get_or_create_player(user_id, username)
    
    welcome_text = (
        "🎮 Добро пожаловать в **Битву Стикеров**!\n\n"
        "⚔️ Это магическая дуэль, где стикеры - твое оружие!\n\n"
        "**Новые функции:**\n"
        "• 🏪 Магазин стикеров\n"
        "• 🏆 Рейтинговая система\n"  
        "• 🎯 Ежедневные задания\n"
        "• 👑 Рейтинговые дуэли\n\n"
        "Выбери действие:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu())

# --- Показать профиль ---
async def show_profile(query, player):
    profile_text = (
        f"🧙 **Профиль мага**\n\n"
        f"👤 Игрок: {player.username}\n"
        f"📈 Уровень: {player.level}\n"
        f"⭐ Опыт: {player.exp}/100\n"
        f"🏅 Рейтинг: {player.rating}⭐\n"
        f"💎 Кристаллы: {player.crystals}\n"
        f"🏆 Побед: {player.wins}\n"
        f"💀 Поражений: {player.losses}\n"
        f"🎯 Наборы стикеров: {len(player.sticker_sets)}\n\n"
        f"Выбери действие:"
    )
    await query.edit_message_text(profile_text, reply_markup=main_menu())

# --- Найти дуэль ---
async def find_duel(query, player_id, ranked=False):
    player = players[player_id]
    
    # Ищем противника
    for other_id, other_player in players.items():
        if (other_id != player_id and 
            other_id not in active_duels and 
            abs(other_player.rating - player.rating) < 200):  # Похожий рейтинг
            
            duel_id = f"{player_id}_{other_id}"
            active_duels[duel_id] = Duel(player_id, other_id, ranked=ranked)
            
            mode_text = "рейтинговую" if ranked else "обычную"
            await query.edit_message_text(f"⚔️ Противник найден! Начинаем {mode_text} дуэль!")
            
            await context.bot.send_message(
                chat_id=other_id,
                text=f"⚔️ Противник найден! Начинаем {mode_text} дуэль!",
                reply_markup=main_menu()
            )
            
            await start_duel_round(context, duel_id)
            return
    
    # Если противник не найден
    mode_text = "рейтинговую" if ranked else "обычную"
    await query.edit_message_text(
        f"⏳ Ищем противника для {mode_text} дуэли... Попробуй позже!",
        reply_markup=main_menu()
    )

# --- Магазин ---
async def handle_shop_purchase(query, player, purchase_type, item_id):
    if purchase_type == 'set':
        if item_id in STICKER_SETS:
            sticker_set = STICKER_SETS[item_id]
            if player.crystals >= sticker_set['cost']:
                player.crystals -= sticker_set['cost']
                player.sticker_sets.append(item_id)
                # Добавляем все стикеры из набора
                for sticker_id in sticker_set['stickers']:
                    if sticker_id not in player.unlocked_stickers[item_id]:
                        player.unlocked_stickers[item_id].append(sticker_id)
                
                await query.message.reply_text(
                    f"✅ Ты купил {sticker_set['name']}!\n"
                    f"💎 Осталось кристаллов: {player.crystals}",
                    reply_markup=main_menu()
                )
            else:
                await query.message.reply_text("❌ Недостаточно кристаллов!")
        else:
            await query.message.reply_text("❌ Набор не найден!")
    
    elif purchase_type == 'sticker':
        if item_id in STICKERS:
            sticker = STICKERS[item_id]
            if player.crystals >= sticker['cost']:
                player.crystals -= sticker['cost']
                if item_id not in player.unlocked_stickers[sticker['set']]:
                    player.unlocked_stickers[sticker['set']].append(item_id)
                
                await query.message.reply_text(
                    f"✅ Ты купил {sticker['name']}!\n"
                    f"💎 Осталось кристаллов: {player.crystals}",
                    reply_markup=main_menu()
                )
            else:
                await query.message.reply_text("❌ Недостаточно кристаллов!")
        else:
            await query.message.reply_text("❌ Стикер не найден!")

# --- Ежедневные задания ---
async def handle_quest_claim(query, player_id):
    quest_info = daily_quests.get(player_id)
    
    if quest_info and quest_info["progress"] >= quest_info["quest"]["target"]:
        reward = quest_info["quest"]["reward"]
        player = players[player_id]
        player.crystals += reward
        player.daily_quests_completed += 1
        
        await query.message.reply_text(
            f"🎉 Задание выполнено!\n"
            f"🎁 Получено: {reward}💎\n"
            f"💎 Всего кристаллов: {player.crystals}"
        )
        
        # Выдаем новое задание
        assign_daily_quest(player_id)
        
    await query.message.reply_text("Выбери действие:", reply_markup=main_menu())

# --- Обновление прогресса заданий ---
def update_quest_progress(player_id, quest_type, amount=1):
    quest_info = daily_quests.get(player_id)
    if quest_info:
        quest = quest_info["quest"]
        if quest["id"] == quest_type:
            quest_info["progress"] = min(quest_info["progress"] + amount, quest["target"])

# --- Обработчик кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = update.effective_user.username or "Игрок"
    
    player = get_or_create_player(user_id, username)
    
    if query.data == 'main_menu':
        await query.edit_message_text("Выберите действие:", reply_markup=main_menu())

    elif query.data == 'find_duel':
        await find_duel(query, user_id, ranked=False)

    elif query.data == 'find_ranked':
        await find_duel(query, user_id, ranked=True)

    elif query.data == 'invite_friend':
        await invite_friend(query, user_id)

    elif query.data == 'profile':
        await show_profile(query, player)

    elif query.data == 'shop':
        await query.edit_message_text("🏪 Магазин стикеров:", reply_markup=shop_menu(user_id))

    elif query.data == 'quests':
        quest_text, markup = quests_menu(user_id)
        await query.edit_message_text(quest_text, reply_markup=markup)

    elif query.data == 'leaderboard':
        leaderboard_text = get_leaderboard()
        await query.edit_message_text(leaderboard_text, reply_markup=main_menu())

    elif query.data.startswith('buy_'):
        parts = query.data.split('_')
        if len(parts) >= 3:
            purchase_type = parts[1]  # 'set' или 'sticker'
            item_id = '_'.join(parts[2:])
            await handle_shop_purchase(query, player, purchase_type, item_id)

    elif query.data == 'claim_quest':
        await handle_quest_claim(query, user_id)

    elif query.data.startswith('sticker_'):
        sticker_id = query.data.replace('sticker_', '')
        await process_sticker_choice(query, sticker_id, user_id, context)

# --- Остальные функции (invite_friend, accept_duel, process_sticker_choice, process_duel_round, end_duel) ---
# Оставляем их без изменений из предыдущего кода, но добавляем обновление рейтинга и заданий

async def end_duel(context, duel_id):
    duel = active_duels[duel_id]
    player1 = players[duel.player1_id]
    player2 = players[duel.player2_id]
    
    if duel.player1_hp <= 0:
        winner = player2
        loser = player1
    else:
        winner = player1
        loser = player2
    
    # Награды
    exp_gain = 25
    crystals_gain = 15
    
    # Обновляем рейтинг для рейтинговых дуэлей
    if duel.ranked:
        rating_change = 25
        winner.rating += rating_change
        loser.rating = max(100, loser.rating - rating_change // 2)
        rating_text = f"📈 Рейтинг: +{rating_change}⭐\n"
    else:
        rating_text = ""
    
    winner.wins += 1
    winner.exp += exp_gain
    winner.crystals += crystals_gain
    
    loser.losses += 1
    loser.exp += exp_gain // 2
    
    # Обновляем прогресс заданий
    update_quest_progress(winner.user_id, "win_3")
    update_quest_progress(loser.user_id, "win_3")
    
    if duel.ranked:
        update_quest_progress(winner.user_id, "win_ranked")
    
    # Проверка повышения уровня
    if winner.exp >= 100:
        winner.level += 1
        winner.exp = 0
        level_up_msg = f"🎉 Поздравляем! Ты достиг {winner.level} уровня!\n"
    else:
        level_up_msg = ""
    
    # Сообщения игрокам
    winner_text = (
        f"🏆 **ПОБЕДА!** 🎉\n\n"
        f"Ты победил {loser.username} в магической дуэли!\n\n"
        f"🎯 Награды:\n"
        f"⭐ +{exp_gain} опыта\n"
        f"💎 +{crystals_gain} кристаллов\n"
        f"{rating_text}"
        f"{level_up_msg}\n"
        f"Выбери следующее действие:"
    )
    
    loser_text = (
        f"💀 **Поражение**\n\n"
        f"Ты проиграл магическую дуэль против {winner.username}\n\n"
        f"🎯 Награды:\n"
        f"⭐ +{exp_gain//2} опыта\n"
        f"{rating_text}"
        f"💪 Не сдавайся! Попробуй снова!\n\n"
        f"Выбери следующее действие:"
    )
    
    for player_id, text in [(winner.user_id, winner_text), (loser.user_id, loser_text)]:
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=text,
                reply_markup=main_menu()
            )
        except Exception as e:
            logger.error(f"Ошибка отправки финального сообщения игроку {player_id}: {e}")
    
    # Удаляем дуэль
    del active_duels[duel_id]

# Добавляем обновление прогресса заданий в process_duel_round
async def process_duel_round(context, duel_id):
    duel = active_duels[duel_id]
    player1 = players[duel.player1_id]
    player2 = players[duel.player2_id]
    
    sticker1 = STICKERS[duel.player1_choice]
    sticker2 = STICKERS[duel.player2_choice]
    
    # Обновляем прогресс заданий для использованных стикеров
    if sticker1["name"] == "🔥 Огненный шар":
        update_quest_progress(duel.player1_id, "use_fireball")
    if sticker2["name"] == "🔥 Огненный шар":
        update_quest_progress(duel.player2_id, "use_fireball")
    
    # ... остальная логика process_duel_round без изменений ...

# HTTP сервер и запуск (оставляем без изменений)
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Sticker Battle Bot is running!')
    
    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.getenv('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"✅ Health server started on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем HTTP сервер в отдельном потоке
    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()
    
    # Запускаем бота
    if not TOKEN:
        logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables")
    else:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("accept", accept_duel))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        logger.info("🎮 Битва Стикеров запускается...")
        application.run_polling()
