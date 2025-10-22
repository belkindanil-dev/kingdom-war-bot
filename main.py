import random
import asyncio
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')

# --- База данных игроков ---
players = {}
active_duels = {}
pending_invites = {}

class Player:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username
        self.level = 1
        self.exp = 0
        self.crystals = 50
        self.wins = 0
        self.losses = 0
        self.sticker_sets = ["basic"]  # Начальный набор
        self.unlocked_stickers = {
            "basic": ["fireball", "icewall", "heal"],
            "lightning": [],
            "dark": [],
            "nature": []
        }

class Duel:
    def __init__(self, player1_id, player2_id):
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.player1_hp = 10
        self.player2_hp = 10
        self.player1_choice = None
        self.player2_choice = None
        self.round = 1
        self.started_at = datetime.now()

# --- Стикеры-заклинания ---
STICKERS = {
    "fireball": {
        "name": "🔥 Огненный шар",
        "type": "attack",
        "power": 3,
        "description": "Наносит 3 ед. урона",
        "set": "basic"
    },
    "icewall": {
        "name": "❄️ Ледяная стена", 
        "type": "defense",
        "power": 2,
        "counter_damage": 1,
        "description": "Блокирует 2 урона, наносит 1 отраженный урон",
        "set": "basic"
    },
    "heal": {
        "name": "💚 Целитель",
        "type": "heal",
        "power": 2,
        "description": "Восстанавливает 2 HP",
        "set": "basic"
    },
    "lightning": {
        "name": "⚡ Удар молнии",
        "type": "attack",
        "power": 4,
        "miss_chance": 0.2,
        "description": "Наносит 4 урона, но может промахнуться",
        "set": "lightning"
    },
    "thunder_shield": {
        "name": "🛡️ Громовой щит",
        "type": "defense", 
        "power": 999,
        "stun": True,
        "cooldown": 3,
        "description": "Блокирует весь урон и оглушает противника",
        "set": "lightning"
    }
}

def get_or_create_player(user_id, username):
    if user_id not in players:
        players[user_id] = Player(user_id, username)
    return players[user_id]

# --- Главное меню ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("⚔️ Найти дуэль", callback_data='find_duel')],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data='invite_friend')],
        [InlineKeyboardButton("📊 Мой профиль", callback_data='profile')],
        [InlineKeyboardButton("🏪 Магазин", callback_data='shop')],
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

# --- Меню принятия дуэли ---
def duel_invite_menu(invite_id):
    buttons = [
        [InlineKeyboardButton("✅ Принять вызов", callback_data=f'accept_{invite_id}')],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f'decline_{invite_id}')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Игрок"
    
    player = get_or_create_player(user_id, username)
    
    welcome_text = (
        "🎮 Добро пожаловать в **Битву Стикеров**!\n\n"
        "⚔️ Это магическая дуэль, где стикеры - твое оружие!\n\n"
        "**Правила:**\n"
        "• Выбирай стикеры-заклинания для атаки, защиты или лечения\n"
        "• Победи того, кто первым опустошит HP противника\n"
        "• Получай кристаллы и открывай новые стикеры!\n\n"
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
        f"💎 Кристаллы: {player.crystals}\n"
        f"🏆 Побед: {player.wins}\n"
        f"💀 Поражений: {player.losses}\n"
        f"🎯 Наборы стикеров: {len(player.sticker_sets)}\n\n"
        f"Выбери действие:"
    )
    await query.edit_message_text(profile_text, reply_markup=main_menu())

# --- Найти случайную дуэль ---
async def find_duel(query, player_id):
    # Ищем другого игрока, который тоже ищет дуэль
    for other_id, other_player in players.items():
        if other_id != player_id and other_id not in active_duels:
            # Создаем дуэль
            duel_id = f"{player_id}_{other_id}"
            active_duels[duel_id] = Duel(player_id, other_id)
            
            # Уведомляем обоих игроков
            await query.edit_message_text("⚔️ Противник найден! Начинаем дуэль!")
            await context.bot.send_message(
                chat_id=other_id,
                text="⚔️ Противник найден! Начинаем дуэль!",
                reply_markup=main_menu()
            )
            
            # Начинаем первый раунд
            await start_duel_round(context, duel_id)
            return
    
    # Если противник не найден
    await query.edit_message_text(
        "⏳ Ищем противника... Попробуй позже или пригласи друга!",
        reply_markup=main_menu()
    )

# --- Пригласить друга ---
async def invite_friend(query, player_id):
    player = players[player_id]
    invite_id = f"{player_id}_{datetime.now().timestamp()}"
    
    pending_invites[invite_id] = {
        "from_player": player_id,
        "to_player": None,  # Будет установлен при принятии
        "created_at": datetime.now()
    }
    
    invite_text = (
        f"🎯 **Приглашение на дуэль**\n\n"
        f"Игрок {player.username} вызывает тебя на магическую дуэль!\n"
        f"Отправь этот код другу: `{invite_id}`\n\n"
        f"Друг должен использовать команду:\n"
        f"`/accept {invite_id}`"
    )
    
    await query.edit_message_text(invite_text, reply_markup=main_menu())

# --- Команда принятия дуэли ---
async def accept_duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Игрок"
    
    if not context.args:
        await update.message.reply_text("❌ Укажи код приглашения: `/accept КОД`")
        return
    
    invite_id = context.args[0]
    
    if invite_id not in pending_invites:
        await update.message.reply_text("❌ Неверный код приглашения или время истекло!")
        return
    
    invite = pending_invites[invite_id]
    from_player_id = invite["from_player"]
    
    if from_player_id == user_id:
        await update.message.reply_text("❌ Нельзя принять собственное приглашение!")
        return
    
    # Создаем дуэль
    duel_id = f"{from_player_id}_{user_id}"
    active_duels[duel_id] = Duel(from_player_id, user_id)
    
    # Удаляем приглашение
    del pending_invites[invite_id]
    
    # Уведомляем обоих игроков
    from_player = players[from_player_id]
    
    await update.message.reply_text(
        f"✅ Ты принял вызов от {from_player.username}! Начинаем дуэль! ⚔️"
    )
    
    await context.bot.send_message(
        chat_id=from_player_id,
        text=f"✅ {username} принял твой вызов! Начинаем дуэль! ⚔️"
    )
    
    # Начинаем дуэль
    await start_duel_round(context, duel_id)

# --- Начало раунда дуэли ---
async def start_duel_round(context, duel_id):
    duel = active_duels[duel_id]
    
    # Отправляем меню выбора стикеров обоим игрокам
    for player_id in [duel.player1_id, duel.player2_id]:
        try:
            player = players[player_id]
            opponent_id = duel.player2_id if player_id == duel.player1_id else duel.player1_id
            opponent = players[opponent_id]
            
            round_text = (
                f"⚔️ **Раунд {duel.round}**\n\n"
                f"❤️ Твое HP: {duel.player1_hp if player_id == duel.player1_id else duel.player2_hp}/10\n"
                f"⚡ HP противника ({opponent.username}): {duel.player2_hp if player_id == duel.player1_id else duel.player1_hp}/10\n\n"
                f"⏱ Выбери стикер за 30 секунд:"
            )
            
            await context.bot.send_message(
                chat_id=player_id,
                text=round_text,
                reply_markup=sticker_menu(player_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения игроку {player_id}: {e}")

# --- Обработка выбора стикера ---
async def process_sticker_choice(query, sticker_id, player_id):
    # Находим активную дуэль игрока
    duel = None
    duel_id = None
    
    for d_id, d in active_duels.items():
        if player_id in [d.player1_id, d.player2_id]:
            duel = d
            duel_id = d_id
            break
    
    if not duel:
        await query.edit_message_text("❌ Дуэль не найдена!", reply_markup=main_menu())
        return
    
    # Сохраняем выбор игрока
    if player_id == duel.player1_id:
        duel.player1_choice = sticker_id
    else:
        duel.player2_choice = sticker_id
    
    await query.edit_message_text(f"✅ Ты выбрал: {STICKERS[sticker_id]['name']}\n⏳ Ждем противника...")
    
    # Проверяем, оба ли игрока сделали выбор
    if duel.player1_choice and duel.player2_choice:
        await process_duel_round(context, duel_id)

# --- Обработка раунда дуэли ---
async def process_duel_round(context, duel_id):
    duel = active_duels[duel_id]
    player1 = players[duel.player1_id]
    player2 = players[duel.player2_id]
    
    sticker1 = STICKERS[duel.player1_choice]
    sticker2 = STICKERS[duel.player2_choice]
    
    # Вычисляем результат раунда
    damage_to_p2 = 0
    damage_to_p1 = 0
    heal_p1 = 0
    heal_p2 = 0
    
    battle_log = []
    
    # Обработка выбора игрока 1
    if sticker1["type"] == "attack":
        if random.random() > sticker1.get("miss_chance", 0):
            damage = sticker1["power"]
            if sticker2["type"] == "defense":
                blocked = min(damage, sticker2["power"])
                damage_to_p2 = damage - blocked
                battle_log.append(f"🔥 {player1.username} атакует {sticker1['name']} ({damage} урона)")
                battle_log.append(f"❄️ {player2.username} блокирует {blocked} урона {sticker2['name']}")
                
                if sticker2.get("counter_damage"):
                    damage_to_p1 = sticker2["counter_damage"]
                    battle_log.append(f"⚡ Отраженный урон: {damage_to_p1} к {player1.username}")
            else:
                damage_to_p2 = damage
                battle_log.append(f"🔥 {player1.username} атакует {sticker1['name']} ({damage} урона)")
        else:
            battle_log.append(f"💫 {player1.username} промахивается с {sticker1['name']}!")
    
    elif sticker1["type"] == "heal":
        heal_p1 = min(sticker1["power"], 10 - duel.player1_hp)
        duel.player1_hp += heal_p1
        battle_log.append(f"💚 {player1.username} восстанавливает {heal_p1} HP")
    
    # Обработка выбора игрока 2
    if sticker2["type"] == "attack":
        if random.random() > sticker2.get("miss_chance", 0):
            damage = sticker2["power"]
            if sticker1["type"] == "defense":
                blocked = min(damage, sticker1["power"])
                damage_to_p1 = damage - blocked
                battle_log.append(f"🔥 {player2.username} атакует {sticker2['name']} ({damage} урона)")
                battle_log.append(f"❄️ {player1.username} блокирует {blocked} урона {sticker1['name']}")
                
                if sticker1.get("counter_damage"):
                    damage_to_p2 = sticker1["counter_damage"]
                    battle_log.append(f"⚡ Отраженный урон: {damage_to_p2} к {player2.username}")
            else:
                damage_to_p1 = damage
                battle_log.append(f"🔥 {player2.username} атакует {sticker2['name']} ({damage} урона)")
        else:
            battle_log.append(f"💫 {player2.username} промахивается с {sticker2['name']}!")
    
    elif sticker2["type"] == "heal":
        heal_p2 = min(sticker2["power"], 10 - duel.player2_hp)
        duel.player2_hp += heal_p2
        battle_log.append(f"💚 {player2.username} восстанавливает {heal_p2} HP")
    
    # Применяем урон
    duel.player1_hp = max(0, duel.player1_hp - damage_to_p1)
    duel.player2_hp = max(0, duel.player2_hp - damage_to_p2)
    
    # Отправляем результаты обоим игрокам
    result_text = "\n".join(battle_log) + f"\n\n❤️ {player1.username}: {duel.player1_hp}/10 HP\n❤️ {player2.username}: {duel.player2_hp}/10 HP"
    
    for player_id in [duel.player1_id, duel.player2_id]:
        try:
            await context.bot.send_message(chat_id=player_id, text=result_text)
        except Exception as e:
            logger.error(f"Ошибка отправки результата игроку {player_id}: {e}")
    
    # Проверяем конец дуэли
    if duel.player1_hp <= 0 or duel.player2_hp <= 0:
        await end_duel(context, duel_id)
    else:
        # Следующий раунд
        duel.round += 1
        duel.player1_choice = None
        duel.player2_choice = None
        await asyncio.sleep(3)
        await start_duel_round(context, duel_id)

# --- Завершение дуэли ---
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
    
    winner.wins += 1
    winner.exp += exp_gain
    winner.crystals += crystals_gain
    
    loser.losses += 1
    loser.exp += exp_gain // 2  # Проигравший получает половину опыта
    
    # Проверка повышения уровня
    if winner.exp >= 100:
        winner.level += 1
        winner.exp = 0
        level_up_msg = f"🎉 Поздравляем! Ты достиг {winner.level} уровня!"
    else:
        level_up_msg = ""
    
    # Сообщения игрокам
    winner_text = (
        f"🏆 **ПОБЕДА!** 🎉\n\n"
        f"Ты победил {loser.username} в магической дуэли!\n\n"
        f"🎯 Награды:\n"
        f"⭐ +{exp_gain} опыта\n"
        f"💎 +{crystals_gain} кристаллов\n"
        f"{level_up_msg}\n\n"
        f"Выбери следующее действие:"
    )
    
    loser_text = (
        f"💀 **Поражение**\n\n"
        f"Ты проиграл магическую дуэль против {winner.username}\n\n"
        f"🎯 Награды:\n"
        f"⭐ +{exp_gain//2} опыта\n"
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

# --- Обработчик кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = update.effective_user.username or "Игрок"
    
    player = get_or_create_player(user_id, username)
    
    if query.data == 'find_duel':
        await find_duel(query, user_id)
    
    elif query.data == 'invite_friend':
        await invite_friend(query, user_id)
    
    elif query.data == 'profile':
        await show_profile(query, player)
    
    elif query.data == 'shop':
        await query.edit_message_text("🏪 Магазин скоро откроется!", reply_markup=main_menu())
    
    elif query.data == 'leaderboard':
        await query.edit_message_text("🏆 Рейтинг скоро появится!", reply_markup=main_menu())
    
    elif query.data.startswith('sticker_'):
        sticker_id = query.data.replace('sticker_', '')
        await process_sticker_choice(query, sticker_id, user_id)

# --- Запуск бота ---
def main():
    if not TOKEN:
        logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("accept", accept_duel))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🎮 Битва Стикеров запускается...")
    application.run_polling()

if __name__ == "__main__":
    main()
