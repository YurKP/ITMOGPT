import json
import uuid
import redis.asyncio as redis
import time

# TTL для persistent-сессий (48 часов)
SESSION_TTL = 48 * 60 * 60  # 172800 секунд

class StateManager:
    # Настройки Кота
    CAT_ROOM_ID = "12_1203"
    CAT_ITEM = {
        "id": "static_npc_cat",
        "type": "static_npc",  # Специальный тип, чтобы нельзя было украсть
        "emoji": "🐈",
        "x": 85, "y": 20,      # Сидит на холодильнике или шкафу
        "by": "Server"
    }

    # Настройки Бессонного Дипломника (босс dorm_stone)
    DORM_STONE_ROOM_ID = "-1_dorm_stone"
    BOSS_ITEM = {
        "id": "static_npc_boss",
        "type": "static_npc",
        "emoji": "🧟‍♂️",
        "x": 50, "y": 40,      # В центре комнаты
        "by": "Server"
    }

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    # --- SESSION (persistent identity) ---
    async def create_session(self, nickname, skin):
        """
        Создает persistent-сессию с уникальным токеном.
        Данные хранятся в Redis с TTL = 48 часов.
        Каждое взаимодействие (connect/move/interact) обновляет TTL.
        Мертвые аккаунты автоматически удаляются Redis'ом по истечении TTL.
        """
        token = str(uuid.uuid4())
        session_data = {
            "token": token,
            "nickname": nickname,
            "skin": skin,
            "created_at": str(int(time.time())),
            "last_seen": str(int(time.time())),
        }
        await self.redis.hset(f"session:{token}", mapping=session_data)
        await self.redis.expire(f"session:{token}", SESSION_TTL)
        return token, session_data

    async def get_session(self, token):
        """Получает сессию по токену. Возвращает None если истекла/не существует."""
        data = await self.redis.hgetall(f"session:{token}")
        return data if data else None

    async def touch_session(self, token):
        """
        Обновляет last_seen и сбрасывает TTL.
        Вызывается при каждом connect — таким образом активные пользователи
        никогда не теряют сессию, а неактивные удаляются через 48ч.
        """
        exists = await self.redis.exists(f"session:{token}")
        if exists:
            await self.redis.hset(f"session:{token}", "last_seen", str(int(time.time())))
            await self.redis.expire(f"session:{token}", SESSION_TTL)
            return True
        return False

    async def delete_session(self, token):
        """Явное удаление сессии (logout)."""
        await self.redis.delete(f"session:{token}")

    # --- USER (live connection, tied to socket sid) ---
    async def update_user(self, sid, user_data):
        # Храним активное подключение socket_id -> user_data
        await self.redis.hset(f"user:{sid}", mapping=user_data)
        # TTL на случай вылета без disconnect (24 часа)
        await self.redis.expire(f"user:{sid}", 86400)

    async def get_user(self, sid):
        return await self.redis.hgetall(f"user:{sid}")

    async def disconnect_user(self, sid):
        """
        При disconnect: убираем из комнаты, удаляем user:{sid}.
        Но session:{token} НЕ удаляем — она живет по своему TTL.
        """
        user = await self.get_user(sid)
        if user and "room_id" in user:
            # Удаляем из списка пользователей комнаты
            await self.redis.srem(f"room:{user['room_id']}:users", sid)
        await self.redis.delete(f"user:{sid}")
        return user

    # --- ROOMS ---
    async def join_room(self, sid, room_id):
        user = await self.get_user(sid)
        if not user: return None
        
        # Если был в другой комнате - выходим
        old_room = user.get("room_id")
        if old_room:
            await self.redis.srem(f"room:{old_room}:users", sid)
        
        # Обновляем данные юзера
        await self.redis.hset(f"user:{sid}", "room_id", room_id)
        # Добавляем в новую комнату
        await self.redis.sadd(f"room:{room_id}:users", sid)
        
        return old_room

    async def get_room_state(self, room_id):
        # 1. Получаем список ID пользователей
        user_ids = await self.redis.smembers(f"room:{room_id}:users")
        users = []
        for uid in user_ids:
            u_data = await self.redis.hgetall(f"user:{uid}")
            if u_data: users.append(u_data)
            
        # 2. Получаем предметы (мусор, записки)
        items_raw = await self.redis.get(f"room:{room_id}:items")
        items = json.loads(items_raw) if items_raw else []

        # if not items:
        #     items = [{"id": "test_1", "emoji": "📦", "x": 50, "y": 50, "by": "System"}]
        #     # Сохраним в Redis, чтобы не генерить вечно
        #     await self.redis.set(f"room:{room_id}:items", json.dumps(items))
        
        # 3. Состояние окружения (свет, пожар)
        env = await self.redis.hgetall(f"room:{room_id}:env")
        if not env: env = {"light": "1"} # 1 = on, 0 = off

        if room_id == self.CAT_ROOM_ID:
            # Проверяем, есть ли кот в списке items
            has_cat = any(i['id'] == self.CAT_ITEM['id'] for i in items)
            if not has_cat:
                items.append(self.CAT_ITEM)
                await self.redis.set(f"room:{room_id}:items", json.dumps(items))

        # Спавн Бессонного Дипломника в dorm_stone (если босс не побежден)
        if room_id == self.DORM_STONE_ROOM_ID:
            boss_defeated = await self.redis.hget(f"room:{room_id}:env", "boss_defeated")
            if boss_defeated != "1":
                has_boss = any(i['id'] == self.BOSS_ITEM['id'] for i in items)
                if not has_boss:
                    items.append(self.BOSS_ITEM)
                    await self.redis.set(f"room:{room_id}:items", json.dumps(items))
            # В dorm_stone всегда темно
            env["light"] = "0"
            
        return {"id": room_id, "users": users, "items": items, "env": env}
    
    # --- INTERACTION ---
    async def add_item(self, room_id, item_data):
        # item_data: {id, type, x, y, emoji}
        items_raw = await self.redis.get(f"room:{room_id}:items")
        items = json.loads(items_raw) if items_raw else []
        
        # Лимит предметов на комнату (чтобы не зафлудили)
        if len(items) > 250: items.pop(0) 
        
        items.append(item_data)
        await self.redis.set(f"room:{room_id}:items", json.dumps(items))
        return items

    async def remove_item(self, room_id, item_id):
        items_raw = await self.redis.get(f"room:{room_id}:items")
        if not items_raw: return []
        items = json.loads(items_raw)
        items = [i for i in items if i['id'] != item_id]
        await self.redis.set(f"room:{room_id}:items", json.dumps(items))
        return items

    async def toggle_light(self, room_id):
        current = await self.redis.hget(f"room:{room_id}:env", "light")
        new_val = "0" if current in {"1", None} else "1"
        await self.redis.hset(f"room:{room_id}:env", "light", new_val)
        return new_val == "1"

    async def get_global_stats(self):
        """
        Проходит по всему Redis и считает людей/пожары по этажам.
        Возвращает: { "1": {"count": 5, "has_fire": False}, "2": ... }
        """
        stats = {}
        
        # 1. Получаем ключи всех комнат, где есть люди
        # Шаблон ключа: room:ЭТАЖ_НОМЕР:users  (напр. room:5_501:users)
        # Или для коридоров: room:floor_5:users
        keys = await self.redis.keys("room:*:users")
        
        for key in keys:
            # key = "room:5_501:users" или "room:floor_5:users"
            parts = key.split(":")
            room_full_id = parts[1]  # "5_501" или "floor_5"
            
            # Парсим номер этажа
            if room_full_id.startswith("floor_"):
                # Коридор: "floor_5" -> этаж "5"
                floor = room_full_id.split("_")[1]
            else:
                # Комната: "5_501" -> этаж "5"
                floor = room_full_id.split("_")[0]
            
            # Считаем людей в этой комнате
            count = await self.redis.scard(key)
            
            # Инициализируем структуру, если её нет
            if floor not in stats:
                stats[floor] = {"count": 0, "has_fire": False}
            
            # Суммируем
            stats[floor]["count"] += count

            # (Опционально) Проверка на пожар
            # Для этого нужно глянуть items этой же комнаты
            # item_key = f"room:{room_full_id}:items"
            # items_raw = await self.redis.get(item_key)
            # if items_raw and "🔥" in items_raw:
            #     stats[floor]["has_fire"] = True

        return stats
