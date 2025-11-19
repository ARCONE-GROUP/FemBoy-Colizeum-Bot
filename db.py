# db.py
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Автоматически определяем путь для контейнера
if os.path.exists('/.dockerenv') or os.path.exists('/app/.dockerenv'):
    DB_PATH = "/app/data/fembo_colos.db"
else:
    DB_PATH = "data/fembo_colos.db"

# Создаем директорию для базы
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ПРИНУДИТЕЛЬНО ДОБАВЛЯЕМ last_adventure ЕСЛИ ЕГО НЕТ
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_adventure TIMESTAMP")
        print("Добавлена колонка last_adventure в таблицу users")
    except sqlite3.OperationalError:
        print("Колонка last_adventure уже существует в users")
        pass


    # Пользователи
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_training TIMESTAMP,
        last_adventure TIMESTAMP
    );
    """)

    # Инвентарь фембоев
    cur.execute("""
    CREATE TABLE IF NOT EXISTS femboy_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        femboy_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        FOREIGN KEY(femboy_id) REFERENCES femboys(id),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );
    """)

    # Фембои
    cur.execute("""
    CREATE TABLE IF NOT EXISTS femboys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        lvl INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        hp INTEGER DEFAULT 50,
        atk INTEGER DEFAULT 10,
        def INTEGER DEFAULT 5,
        gold INTEGER DEFAULT 30,
        weapon_atk INTEGER DEFAULT 0,
        armor_def INTEGER DEFAULT 0,
        current_boss INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS duels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenger_id INTEGER NOT NULL,
        opponent_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending', -- pending, accepted, finished
        winner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS adventures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        femboy_id INTEGER NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        completed BOOLEAN DEFAULT 0,
        chat_id INTEGER NOT NULL,
        FOREIGN KEY(femboy_id) REFERENCES femboys(id)
    );
    """)

    # Магазин
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        value INTEGER NOT NULL,
        price INTEGER NOT NULL

    );
    """)
    try:
        cur.execute("ALTER TABLE items ADD COLUMN rarity TEXT DEFAULT 'common'")
        print("Добавлена колонка rarity в items")
    except sqlite3.OperationalError:
        print("Колонка rarity уже существует")
        pass

    def calculate_price(rarity, value, item_type, is_special=False):
        """Рассчитывает цену предмета"""
        base_prices = {'trash': 80, 'toy': 120, 'wooden': 200, 'common': 300, 'rare': 500, 'mythical': 1000, 'divine': 2000}
        type_multipliers = {'weapon': 1.2, 'armor': 1.0, 'special': 1.5}
        stats_multiplier = 1 + (value * 0.15)
        special_multiplier = 1.4 if is_special else 1.0
        price = base_prices[rarity] * stats_multiplier * type_multipliers[item_type] * special_multiplier
        return max(80, int(price))


    print("=== ОБНОВЛЕНИЕ РЕДКОСТЕЙ ПРЕДМЕТОВ ===")

    # Обновляем редкости по имени
    rarity_updates = [
        ('trash', ['Говорящая рыба', 'Тапочки безумия', 'Ватная палочка', 'Бычий Член', 'Митенки']),
        ('toy', ['Волшебный Жезл', 'Костюм горничной', 'Интегральная пушка', 'Чокер с поводком', 'Пособие по python']),
        ('wooden', ['Кошачьи ушки', 'Халяль Редбулл', 'Дырявый Тазик', 'Накидка из Фольги', 'Нунчaки из Багетов']),
        ('common', ['Меч Астольфо']),
        ('rare', ['Благородная Слизь']),
        ('adventure', ['Потертый плащ', 'Зачарованный амулет', 'Острые когти', 'Древний свиток', 'Блестящее кольцо', 'Магический жезл'])
    ]

    for rarity, names in rarity_updates:
        for name in names:
            cur.execute("UPDATE items SET rarity = ? WHERE name = ?", (rarity, name))
            print(f"Обновлена редкость: {name} -> {rarity}")

    # Список ВСЕХ предметов которые должны быть в игре
    all_items = [
        ("Говорящая рыба", "weapon", 1, calculate_price('trash', 1, 'weapon'), "trash"),
        ("Тапочки безумия", "armor", 2, calculate_price('trash', 2, 'armor'), "trash"),
        ("Ватная палочка", "weapon", 2, calculate_price('trash', 2, 'weapon'), "trash"),
        ("Бычий Член", "weapon", 3, calculate_price('trash', 3, 'weapon'), "trash"),
        ("Митенки", "armor", 3, calculate_price('trash', 3, 'armor'), "trash"),
        ("Волшебный Жезл", "weapon", 9, calculate_price('toy', 9, 'weapon'), "toy"),
        ("Костюм горничной", "armor", 9, calculate_price('toy', 9, 'armor'), "toy"),
        ("Интегральная пушка", "weapon", 12, calculate_price('toy', 12, 'weapon'), "toy"),
        ("Чокер с поводком", "armor", 15, calculate_price('toy', 15, 'armor'), "toy"),
        ("Пособие по python", "weapon", 17, calculate_price('toy', 17, 'weapon'), "toy"),
        ("Кошачьи ушки", "armor", 20, calculate_price('wooden', 20, 'armor'), "wooden"),
        ("Халяль Редбулл", "weapon", 25 , calculate_price('wooden', 25, 'weapon'), "wooden"),
        ("Дырявый Тазик", "armor", 27, calculate_price('wooden', 27, 'armor'), "wooden"),
        ("Накидка из Фольги", "armor", 32, calculate_price('wooden', 32, 'armor'), "wooden"),
        ("Нунчaки из Багетов", "weapon", 35, calculate_price('wooden', 35, 'weapon'), "wooden"),
        ("Меч Астольфо", "weapon", 50, calculate_price('common', 50, 'weapon'), "common"),
        ("Благородная Слизь", "armor", 100, calculate_price('rare', 100, 'armor'), "rare"),
        # Приключенческие предметы
        ("Потертый плащ", "armor", 2, 0, "adventure"),
        ("Зачарованный амулет", "armor", 5, 0, "adventure"),
        ("Острые когти", "weapon", 3, 0, "adventure"),
        ("Древний свиток", "weapon", 7, 0, "adventure"),
        ("Блестящее кольцо", "armor", 3, 0, "adventure"),
        ("Магический жезл", "weapon", 10, 0, "adventure")
    ]

    print("Добавление недостающих предметов...")
    for item in all_items:
        cur.execute("SELECT id FROM items WHERE name = ?", (item[0],))
        if not cur.fetchone():
            cur.execute("INSERT INTO items (name, type, value, price, rarity) VALUES (?, ?, ?, ?, ?)", item)
            print(f"Добавлен новый предмет: {item[0]} ({item[4]})")
        else:
            print(f"Предмет уже существует: {item[0]}")

    print("=== ОБНОВЛЕНИЕ ПРЕДМЕТОВ ЗАВЕРШЕНО ===")
            
    # Битвы
    cur.execute("""
    CREATE TABLE IF NOT EXISTS battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        femboy_a INTEGER,
        femboy_b INTEGER,
        winner INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS adventure_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adventure_id INTEGER NOT NULL,
        event_text TEXT NOT NULL,
        xp_gained INTEGER DEFAULT 0,
        gold_gained INTEGER DEFAULT 0,
        item_found TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(adventure_id) REFERENCES adventures(id)
    );
    """)

    conn.commit()
    return conn

# === Пользователи ===
def get_user_by_tid(conn, tid: int) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
    return cur.fetchone()

def create_user(conn, tid: int, username: str = None):
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)", (tid, username))
    conn.commit()
    return get_user_by_tid(conn, tid)

def add_missing_columns(conn):
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE femboys ADD COLUMN weapon_atk INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # колонка уже есть
    try:
        cur.execute("ALTER TABLE femboys ADD COLUMN armor_def INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()


# === Фембои ===
def create_femboy(conn, user_id: int, name: str) -> sqlite3.Row:
    cur = conn.cursor()
    cur.execute("INSERT INTO femboys (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    cur.execute("SELECT * FROM femboys WHERE id = last_insert_rowid()")
    return cur.fetchone()

def get_femboy_by_user(conn, user_id: int) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM femboys WHERE user_id=?", (user_id,))
    return cur.fetchone()

def list_other_femboys(conn, exclude_user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT f.*, u.username FROM femboys f JOIN users u ON f.user_id=u.id WHERE f.user_id != ?", (exclude_user_id,))
    return cur.fetchall()

def get_femboy_dict(conn, user_id: int) -> Optional[dict]:
    f = get_femboy_by_user(conn, user_id)
    if not f:
        return None
    
    d = dict(f)
    # Динамически рассчитываем бонусы
    from bot_utils import calculate_equipment_bonuses
    bonuses = calculate_equipment_bonuses(conn, d["id"])
    
    d.setdefault("lvl", 1)
    d.setdefault("xp", 0)
    d.setdefault("hp", 50)
    d.setdefault("atk", 10)
    d.setdefault("def", 5)
    d.setdefault("gold", 30)
    d["weapon_atk"] = bonuses['weapon']
    d["armor_def"] = bonuses['armor'] 
    
    return d

def get_femboy_by_id(conn, femboy_id: int):
    cur = conn.cursor()
    cur.execute("SELECT * FROM femboys WHERE id=?", (femboy_id,))
    return cur.fetchone()

# === Битвы ===
def record_battle(conn, a_id: int, b_id: int, winner_id: int):
    cur = conn.cursor()
    cur.execute("INSERT INTO battles (femboy_a, femboy_b, winner) VALUES (?, ?, ?)", (a_id, b_id, winner_id))
    conn.commit()

# === Тренировка ===
def get_last_training(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT last_training FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row and row["last_training"]:
        return datetime.fromisoformat(row["last_training"])
    return None

def can_train(conn, user_id: int):
    last = get_last_training(conn, user_id)
    if not last:
        return True
    return datetime.now() - last > timedelta(days=1)

def update_training_time(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_training=? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()

def update_warrior(conn, femboy_id: int, data: dict):
    cur = conn.cursor()
    fields = []
    values = []
    for key, val in data.items():
        fields.append(f"{key}=?")
        values.append(val)
    values.append(femboy_id)
    cur.execute(f"UPDATE femboys SET {', '.join(fields)} WHERE id=?", values)
    conn.commit()

def get_user_by_username(conn, username: str):
    username = username.lstrip("@")  # убираем @ если есть
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    return cur.fetchone()


# === Приключения ===
def get_last_adventure(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT last_adventure FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if row and row["last_adventure"]:
        return datetime.fromisoformat(row["last_adventure"])
    return None

def can_adventure(conn, user_id: int):
    last = get_last_adventure(conn, user_id)
    if not last:
        return True
    return datetime.now() - last > timedelta(days=1)

def update_adventure_time(conn, user_id: int):
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_adventure=? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()


def add_missing_columns(conn):
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE femboys ADD COLUMN weapon_atk INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE femboys ADD COLUMN armor_def INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE adventures ADD COLUMN chat_id INTEGER")  # ← ДОБАВЬ
    except sqlite3.OperationalError:
        pass
    conn.commit()