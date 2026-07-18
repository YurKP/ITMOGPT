import os
import socketio
import uuid
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .state_manager import StateManager
from .analytics import log
from .ai_reports import generate_admin_report, generate_newspaper, get_dorm_summary_for_itmogpt

async def broadcast_stats():
    stats = await mgr.get_global_stats()
    await sio.emit("global_stats", stats)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "changeme")
mgr = StateManager(REDIS_URL)

ALLOWED_ORIGINS = [
    "https://xn--80abcgk4c7d.fun",
    "*",
]

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=ALLOWED_ORIGINS,
    ping_interval=25,
    ping_timeout=60,
)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
sio_app = socketio.ASGIApp(sio, app)

MOUNT_PATH = "/socket.io/"

app.add_route(MOUNT_PATH, route=sio_app, methods=["GET", "POST"])
app.mount(MOUNT_PATH, sio_app)


# ============================================================
# REST API: AI Reports, Newspaper, ITMO GPT integration
# ============================================================

@app.get("/api/admin/report")
async def admin_report(secret: str = Query(""), hours: int = Query(24)):
    if secret != ADMIN_SECRET:
        return {"error": "Unauthorized"}
    result = await generate_admin_report(hours)
    return result


@app.get("/api/newspaper")
async def newspaper(hours: int = Query(24)):
    result = await generate_newspaper(hours)
    return result


@app.get("/api/dorm-summary")
async def dorm_summary():
    return await get_dorm_summary_for_itmogpt()


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return ADMIN_HTML


@app.get("/newspaper", response_class=HTMLResponse)
async def newspaper_page():
    return NEWSPAPER_HTML


ADMIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Вобщаге — Админка</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#1a1a2e;color:#e0e0e0;min-height:100vh}
.container{max-width:800px;margin:0 auto;padding:20px}
h1{text-align:center;font-size:2rem;margin:20px 0;color:#ffd600;text-transform:uppercase;letter-spacing:3px}
.subtitle{text-align:center;color:#888;margin-bottom:30px}
.controls{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;justify-content:center}
input,select{font-family:inherit;padding:10px 16px;border:3px solid #333;background:#0d0d1a;color:#e0e0e0;font-size:1rem}
button{font-family:inherit;padding:10px 24px;border:3px solid #ffd600;background:#ffd600;color:#000;font-weight:bold;text-transform:uppercase;cursor:pointer;box-shadow:4px 4px 0 #000;transition:all .1s}
button:active{box-shadow:0 0 0;transform:translate(4px,4px)}
button:disabled{opacity:.5;cursor:wait}
.report-box{border:3px solid #333;background:#0d0d1a;padding:20px;margin-top:20px;white-space:pre-wrap;line-height:1.6;min-height:200px}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:20px}
.stat-card{border:2px solid #333;padding:12px;background:#16213e}
.stat-card h3{color:#ffd600;font-size:.85rem;margin-bottom:6px}
.stat-card .value{font-size:1.5rem;font-weight:bold}
.loading{text-align:center;padding:40px;color:#ffd600;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.error{color:#ff4444;padding:20px;border:2px solid #ff4444}
footer{text-align:center;margin-top:40px;color:#444;font-size:.8rem}
</style>
</head>
<body>
<div class="container">
<h1>🏠 Вобщаге — Админка</h1>
<p class="subtitle">AI-рапорт для коменданта</p>
<div class="controls">
<input type="password" id="secret" placeholder="Секретный ключ">
<select id="hours"><option value="24">24 часа</option><option value="12">12 часов</option><option value="48">48 часов</option></select>
<button id="genBtn" onclick="generateReport()">📊 Сгенерировать рапорт</button>
</div>
<div id="statsGrid" class="stats-grid"></div>
<div id="reportBox" class="report-box">Нажмите кнопку для генерации AI-рапорта...</div>
<footer>Вобщаге · AI Analytics · Powered by LLM</footer>
</div>
<script>
async function generateReport(){
const btn=document.getElementById('genBtn');
const box=document.getElementById('reportBox');
const grid=document.getElementById('statsGrid');
const secret=document.getElementById('secret').value;
const hours=document.getElementById('hours').value;
btn.disabled=true;
box.innerHTML='<div class="loading">🤖 Генерирую рапорт...</div>';
grid.innerHTML='';
try{
const r=await fetch('/api/admin/report?secret='+encodeURIComponent(secret)+'&hours='+hours);
const d=await r.json();
if(d.error){box.innerHTML='<div class="error">❌ '+d.error+'</div>';return}
box.textContent=d.report;
const s=d.stats;
let cards='';
cards+='<div class="stat-card"><h3>📊 Событий</h3><div class="value">'+s.total_events+'</div></div>';
const online=Object.values(s.online_by_floor||{}).reduce((a,b)=>a+b,0);
cards+='<div class="stat-card"><h3>👥 Онлайн</h3><div class="value">'+online+'</div></div>';
const floors=Object.keys(s.online_by_floor||{}).length;
cards+='<div class="stat-card"><h3>🏢 Этажей</h3><div class="value">'+floors+'</div></div>';
const issues=Object.keys(s.floor_issues||{}).length;
cards+='<div class="stat-card"><h3>⚠️ Проблем</h3><div class="value">'+issues+'</div></div>';
grid.innerHTML=cards;
}catch(e){box.innerHTML='<div class="error">❌ Ошибка: '+e.message+'</div>'}
finally{btn.disabled=false}
}
</script>
</body>
</html>"""


NEWSPAPER_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Слухи Общаги 🗞️</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#fef3c7;color:#1a1a1a;min-height:100vh}
.container{max-width:700px;margin:0 auto;padding:20px}
.masthead{text-align:center;border-bottom:4px double #000;padding-bottom:16px;margin-bottom:20px}
.masthead h1{font-size:2.5rem;letter-spacing:2px;text-transform:uppercase}
.masthead .date{color:#666;font-size:.9rem;margin-top:4px}
.edition{text-align:center;font-size:.8rem;color:#888;margin-bottom:20px;font-style:italic}
.controls{display:flex;gap:12px;margin-bottom:20px;justify-content:center}
button{font-family:inherit;padding:12px 28px;border:3px solid #000;background:#ffd600;color:#000;font-weight:bold;text-transform:uppercase;cursor:pointer;box-shadow:4px 4px 0 #000;transition:all .1s;font-size:1rem}
button:active{box-shadow:0 0 0;transform:translate(4px,4px)}
button:disabled{opacity:.5;cursor:wait}
.newspaper-content{border:3px solid #000;background:#fff;padding:24px;line-height:1.7;white-space:pre-wrap;min-height:300px;box-shadow:6px 6px 0 #000}
.loading{text-align:center;padding:40px;font-size:1.2rem;animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.stats-bar{display:flex;gap:16px;justify-content:center;margin:16px 0;flex-wrap:wrap}
.stats-bar .chip{border:2px solid #000;padding:4px 12px;background:#e0f2fe;font-size:.85rem;font-weight:bold}
footer{text-align:center;margin-top:30px;color:#999;font-size:.75rem;border-top:2px solid #ccc;padding-top:12px}
</style>
</head>
<body>
<div class="container">
<div class="masthead">
<h1>🗞️ Слухи Общаги</h1>
<div class="date" id="dateStr"></div>
</div>
<p class="edition">Ежедневная AI-газета общежития ИТМО</p>
<div class="controls">
<button id="genBtn" onclick="generate()">📰 Свежий выпуск!</button>
</div>
<div id="statsBar" class="stats-bar"></div>
<div class="newspaper-content" id="content">Нажми кнопку, чтобы получить свежий выпуск! 🗞️</div>
<footer>Слухи Общаги · Генерируется нейросетью · вобщаге.fun</footer>
</div>
<script>
document.getElementById('dateStr').textContent=new Date().toLocaleDateString('ru-RU',{weekday:'long',year:'numeric',month:'long',day:'numeric'});
async function generate(){
const btn=document.getElementById('genBtn');
const box=document.getElementById('content');
const bar=document.getElementById('statsBar');
btn.disabled=true;
box.innerHTML='<div class="loading">🤖 Печатаем свежий номер...</div>';
bar.innerHTML='';
try{
const r=await fetch('/api/newspaper');
const d=await r.json();
box.textContent=d.newspaper;
const s=d.stats;
let chips='';
chips+='<span class="chip">📊 '+s.total_events+' событий</span>';
const rooms=s.top_rooms_activity?.length||0;
chips+='<span class="chip">🏠 '+rooms+' активных комнат</span>';
const topEmoji=s.top_emoji?.[0];
if(topEmoji)chips+='<span class="chip">🏆 '+topEmoji[0]+' ('+topEmoji[1]+'x)</span>';
bar.innerHTML=chips;
}catch(e){box.textContent='❌ Ошибка: '+e.message}
finally{btn.disabled=false}
}
</script>
</body>
</html>"""


import random

# Словари
ADJECTIVES = ["Дикий", "Грязный", "Уставший", "Потный", "Вечный", "Лютый", "Ночной"]
NOUNS = ["Пупсик", "Перфак", "Таракан", "Доширак", "Сосед", "Вахтер", "Клоп", "Доцент"]

# --- ПАСХАЛКИ: Факультеты Распределяющей Шляпы ---
FACULTIES = [
    {"name": "Роллтондор", "emoji": "🟥", "desc": "Храбрые, доедают чужую еду"},
    {"name": "Дедлайнерин", "emoji": "🟩", "desc": "Хитрые, сдают лабы в 23:59"},
    {"name": "Пиводуй", "emoji": "🟨", "desc": "Добрые, вечно тусят на кухне"},
    {"name": "Ботанвран", "emoji": "🟦", "desc": "Умные, их никто никогда не видел"},
]

# --- ПАСХАЛКИ: Комната Общажного Камня ---
DORM_STONE_ROOM = "-1_dorm_stone"
BOSS_NPC_ID = "static_npc_boss"
GEM_ITEM_ID = "static_gem_stone"

# --- Хранилище IP по sid (environ доступен только в connect) ---
_sid_ip = {}

def _get_ip(environ):
    """Извлекает IP из ASGI/WSGI environ. Учитывает X-Forwarded-For от nginx."""
    # X-Forwarded-For может быть в разных форматах
    if isinstance(environ, dict):
        # ASGI scope
        headers = {}
        for key, val in environ.get("asgi.scope", {}).get("headers", []):
            if isinstance(key, bytes):
                headers[key.decode().lower()] = val.decode() if isinstance(val, bytes) else val
            else:
                headers[str(key).lower()] = str(val)
        
        xff = headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
        
        xri = headers.get("x-real-ip", "")
        if xri:
            return xri.strip()
        
        # Fallback: REMOTE_ADDR из environ
        remote = environ.get("REMOTE_ADDR", "")
        if remote:
            return remote
        
        # ASGI scope client
        scope = environ.get("asgi.scope", {})
        client = scope.get("client")
        if client:
            return client[0]
    
    return "unknown"


@sio.event
async def login(sid, data):
    """
    Логин: проверяет пароль, генерирует ник + создает persistent session.
    Возвращает token, который клиент сохраняет в localStorage.
    """
    ip = _sid_ip.get(sid, "unknown")
    
    # 1. ПРОВЕРКА ПАРОЛЯ
    if data.get("password", "").lower().strip() != "белка":
        log("login_fail", sid=sid, ip=ip, answer=data.get("password", ""))
        return {"status": "error", "msg": "Неверно! Ты не из наших."}
    
    # 2. ГЕНЕРАЦИЯ НИКА
    attempts = 0
    nickname = ""
    while attempts < 10:
        adj = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        extra = random.choice(ADJECTIVES) + " " if attempts > 5 else ""
        nickname = f"{extra}{adj} {noun}"
        if attempts > 8:
            nickname += f"_{random.randint(1,99)}"
        break
        
    skin = data.get("skin", "😐")
    
    # 3. СОЗДАЕМ PERSISTENT SESSION в Redis (живет 48ч)
    token, session = await mgr.create_session(nickname, skin)
    
    # 4. Создаем live user (привязан к текущему sid)
    user_data = {
        "sid": sid,
        "token": token,
        "nickname": nickname,
        "skin": skin,
        "x": 50, "y": 50,
        "room_id": ""
    }
    await mgr.update_user(sid, user_data)
    
    log("login", sid=sid, ip=ip, nickname=nickname, skin=skin, token=token[:8])
    
    await sio.emit("me", user_data, to=sid)
    await broadcast_stats()
    
    return {"status": "ok", "token": token}


@sio.event
async def restore_session(sid, data):
    """
    Восстановление сессии по токену из localStorage.
    """
    ip = _sid_ip.get(sid, "unknown")
    token = data.get("token", "") if isinstance(data, dict) else data
    if not token:
        log("restore_fail", sid=sid, ip=ip, reason="no_token")
        return {"status": "error", "msg": "no_token"}
    
    session = await mgr.get_session(token)
    if not session:
        log("restore_fail", sid=sid, ip=ip, reason="session_expired", token=token[:8])
        return {"status": "error", "msg": "session_expired"}
    
    await mgr.touch_session(token)
    
    user_data = {
        "sid": sid,
        "token": token,
        "nickname": session["nickname"],
        "skin": session["skin"],
        "x": 50, "y": 50,
        "room_id": ""
    }
    # Восстанавливаем пасхальные данные из сессии
    if session.get("has_gem"):
        user_data["has_gem"] = session["has_gem"]
    if session.get("faculty"):
        user_data["faculty"] = session["faculty"]
    if session.get("unlocked_basement"):
        user_data["unlocked_basement"] = session["unlocked_basement"]
    
    await mgr.update_user(sid, user_data)
    
    log("restore", sid=sid, ip=ip, nickname=session["nickname"], skin=session["skin"], token=token[:8])
    
    await sio.emit("me", user_data, to=sid)
    await broadcast_stats()
    
    return {"status": "ok", "token": token}


@sio.event
async def connect(sid, environ, auth):
    """
    При подключении сохраняем IP и логируем.
    Клиент сам решает: restore_session или login.
    """
    ip = _get_ip(environ)
    _sid_ip[sid] = ip
    log("connect", sid=sid, ip=ip)


@sio.event
async def join_room(sid, room_id):
    user = await mgr.get_user(sid)
    ip = _sid_ip.get(sid, "unknown")
    nickname = user.get("nickname", "") if user else ""
    
    # --- СЕРВЕРНАЯ ПРОВЕРКА: доступ к -1 этажу ---
    # Если room_id начинается с "-1" или "floor_-1", проверяем unlocked_basement
    if room_id.startswith("-1") or room_id == "floor_-1":
        unlocked = await mgr.redis.hget(f"user:{sid}", "unlocked_basement")
        if unlocked != "1":
            log("join_room_denied", sid=sid, ip=ip, nickname=nickname, room_id=room_id, reason="basement_locked")
            await sio.emit("notification", "🔒 Подвал заперт. Найди способ открыть его...", to=sid)
            return
    
    log("join_room", sid=sid, ip=ip, nickname=nickname, room_id=room_id)
    
    old_room = await mgr.join_room(sid, room_id)
    if old_room:
        await sio.leave_room(sid, old_room)
        await sio.emit("user_left", {"sid": sid}, room=old_room)

    await sio.enter_room(sid, room_id)
    
    state = await mgr.get_room_state(room_id)
    await sio.emit("room_state", state, to=sid)
    
    me = await mgr.get_user(sid)
    # Отправляем user_joined только ДРУГИМ пользователям в комнате (skip_sid),
    # т.к. текущий пользователь уже получил себя в room_state
    await sio.emit("user_joined", me, room=room_id, skip_sid=sid)
    await broadcast_stats()

@sio.event
async def move(sid, data):
    # move не логируем — слишком частое событие, засорит логи
    await mgr.redis.hset(f"user:{sid}", mapping={"x": data['x'], "y": data['y']})
    user = await mgr.get_user(sid)
    if user and "room_id" in user:
        room_id = user['room_id']
        await sio.emit("user_moved", {"sid": sid, "x": data['x'], "y": data['y']}, room=room_id, skip_sid=sid)
        
        # --- ПАСХАЛКА: Проверка близости к Бессонному Дипломнику в dorm_stone ---
        if room_id == DORM_STONE_ROOM:
            boss_defeated = await mgr.redis.hget(f"room:{DORM_STONE_ROOM}:env", "boss_defeated")
            if boss_defeated != "1":
                boss_x, boss_y = 50, 40
                dist_x = abs(float(data['x']) - boss_x)
                dist_y = abs(float(data['y']) - boss_y)
                
                if dist_x < 10 and dist_y < 10:
                    # Слишком близко к дипломнику — телепорт на 1 этаж!
                    await sio.emit("boss_teleport", {
                        "msg": "🧟‍♂️ НЕ МЕШАЙ, ДЕДЛАЙН ЗАВТРА! *выкидывает тебя из комнаты*"
                    }, to=sid)

@sio.event
async def interact(sid, data):
    user = await mgr.get_user(sid)
    room_id = user.get("room_id")
    ip = _sid_ip.get(sid, "unknown")
    nickname = user.get("nickname", "") if user else ""

    # --- ПАСХАЛКА 1: Распределяющая Шляпа (работает из коридора -1 этажа) ---
    if data['type'] == 'sorting_hat':
        # Серверная проверка: игрок должен быть на -1 этаже
        if not room_id or not (room_id.startswith("-1") or room_id == "floor_-1"):
            return
        
        # Проверяем, не был ли уже распределен
        existing_faculty = await mgr.redis.hget(f"user:{sid}", "faculty")
        if existing_faculty:
            await sio.emit("notification", f"🎩 Шляпа ворчит: Ты уже в {existing_faculty}!", to=sid)
            return
        
        # Выбираем случайный факультет
        faculty = random.choice(FACULTIES)
        faculty_name = faculty["name"]
        faculty_emoji = faculty["emoji"]
        
        # Обновляем никнейм
        new_nickname = f"[{faculty_name}] {nickname}"
        await mgr.redis.hset(f"user:{sid}", mapping={
            "nickname": new_nickname,
            "faculty": faculty_name
        })
        
        # Обновляем persistent session тоже
        token = user.get("token", "")
        if token:
            await mgr.redis.hset(f"session:{token}", "nickname", new_nickname)
        
        log("sorting_hat", sid=sid, ip=ip, nickname=nickname, faculty=faculty_name)
        
        # Уведомляем самого игрока
        await sio.emit("sorting_hat_result", {
            "faculty": faculty_name,
            "emoji": faculty_emoji,
            "desc": faculty["desc"],
            "new_nickname": new_nickname
        }, to=sid)
        
        # Обновляем ник для всех в комнате
        await sio.emit("user_nickname_changed", {
            "sid": sid,
            "nickname": new_nickname
        }, room=room_id)
        
        # Глобальное уведомление
        await sio.emit("notification", f"🎩 Шляпа кричит: {faculty_emoji} {faculty_name.upper()}! ({nickname})")
        
        # Обновляем me для клиента
        updated_user = await mgr.get_user(sid)
        await sio.emit("me", updated_user, to=sid)
        return

    if not room_id: return

    if data['type'] == 'toggle_light':
        # В комнате dorm_stone свет нельзя включить
        if room_id == DORM_STONE_ROOM:
            await sio.emit("notification", "💡 Кнопка не работает... Что-то блокирует свет.", to=sid)
            return
        is_on = await mgr.toggle_light(room_id)
        await sio.emit("light_update", is_on, room=room_id)
        log("interact", sid=sid, ip=ip, nickname=nickname, room_id=room_id, action="toggle_light", light_on=is_on)
        
    elif data['type'] == 'add_item':
        item_id = str(uuid.uuid4())
        emoji = data['payload'].get('emoji', '💩')
        
        # Если у игрока есть Общажный Камень — заменяем мусор на золото (на обычных этажах)
        has_gem = await mgr.redis.hget(f"user:{sid}", "has_gem")
        if has_gem == "1" and not room_id.startswith("-1"):
            emoji = "💰"
        
        item = {
            "id": item_id,
            "emoji": emoji,
            "x": data['payload']['x'],
            "y": data['payload']['y'],
            "by": user['nickname']
        }
        await mgr.add_item(room_id, item)
        await sio.emit("item_added", item, room=room_id)
        
        log("interact", sid=sid, ip=ip, nickname=nickname, room_id=room_id, action="add_item", emoji=emoji)

        # --- Проверка гитары рядом с боссом в dorm_stone ---
        if room_id == DORM_STONE_ROOM and emoji == '🎸':
            boss_defeated = await mgr.redis.hget(f"room:{DORM_STONE_ROOM}:env", "boss_defeated")
            if boss_defeated != "1":
                # Проверяем расстояние до босса (босс в центре: 50, 40)
                boss_x, boss_y = 50, 40
                dist_x = abs(float(item['x']) - boss_x)
                dist_y = abs(float(item['y']) - boss_y)
                
                if dist_x < 15 and dist_y < 15:
                    # Босс побежден!
                    await mgr.redis.hset(f"room:{DORM_STONE_ROOM}:env", "boss_defeated", "1")
                    
                    # Удаляем босса из items
                    await mgr.remove_item(DORM_STONE_ROOM, BOSS_NPC_ID)
                    await sio.emit("item_removed", BOSS_NPC_ID, room=DORM_STONE_ROOM)
                    
                    # Спавним Общажный Камень на месте босса
                    gem_item = {
                        "id": GEM_ITEM_ID,
                        "type": "gem",
                        "emoji": "💎",
                        "x": boss_x,
                        "y": boss_y,
                        "by": "Server"
                    }
                    await mgr.add_item(DORM_STONE_ROOM, gem_item)
                    await sio.emit("item_added", gem_item, room=DORM_STONE_ROOM)
                    
                    # Уведомление в комнате
                    await sio.emit("notification", f"🎸 «Батарейка» усыпила Дипломника 😴! На полу появился 💎 Общажный Камень!", room=DORM_STONE_ROOM)
                    await sio.emit("boss_defeated", {}, room=DORM_STONE_ROOM)
                    
                    log("boss_defeated", sid=sid, ip=ip, nickname=nickname)
                    return

        is_pizza = item['emoji'] == '🍕'
        is_cat_room = room_id == "12_1203"
        
        if is_pizza and is_cat_room:
            cat_x, cat_y = 85, 20
            dist_x = abs(item['x'] - cat_x)
            dist_y = abs(item['y'] - cat_y)

            if dist_x < 15 and dist_y < 15:
                await mgr.redis.hset(f"user:{sid}", "unlocked_basement", "1")
                await sio.emit("achievement_unlocked", {"id": "basement"}, to=sid)
                await sio.emit('notification', f"🐈 {user['nickname']} открыл секретный проход!", room=room_id)
                log("achievement", sid=sid, ip=ip, nickname=nickname, achievement="basement")
                return

    elif data['type'] == 'remove_item':
        item_id = data['payload'].get('id')
        # Нельзя удалить кота, босса
        if item_id in ('static_npc_cat', BOSS_NPC_ID):
            return
        
        # Подбор Общажного Камня
        if item_id == GEM_ITEM_ID and room_id == DORM_STONE_ROOM:
            # Игрок подбирает камень!
            await mgr.redis.hset(f"user:{sid}", "has_gem", "1")
            
            # Обновляем persistent session
            token = user.get("token", "")
            if token:
                await mgr.redis.hset(f"session:{token}", "has_gem", "1")
            
            await mgr.remove_item(room_id, item_id)
            await sio.emit("item_removed", item_id, room=room_id)
            
            # Уведомляем игрока
            await sio.emit("gem_collected", {"sid": sid}, to=sid)
            
            # Глобальное уведомление на всю общагу
            await sio.emit("notification", f"⚡️ {nickname} добыл Общажный Камень! 💎")
            
            log("gem_collected", sid=sid, ip=ip, nickname=nickname)
            return
        
        await mgr.remove_item(room_id, item_id)
        await sio.emit("item_removed", item_id, room=room_id)
        log("interact", sid=sid, ip=ip, nickname=nickname, room_id=room_id, action="remove_item", item_id=item_id)

@sio.event
async def disconnect(sid):
    user = await mgr.disconnect_user(sid)
    ip = _sid_ip.pop(sid, "unknown")
    nickname = user.get("nickname", "") if user else ""
    
    if user and user.get("room_id"):
        await sio.emit("user_left", {"sid": sid}, room=user['room_id'])
    await broadcast_stats()
    
    log("disconnect", sid=sid, ip=ip, nickname=nickname)
