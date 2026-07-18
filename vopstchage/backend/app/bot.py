import asyncio
import socketio
import random
import os

# Получаем URL бэкенда из переменных окружения (или дефолт для локального запуска)
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')

async def run_bot(bot_id):
    sio = socketio.AsyncClient()
    
    # Генерация личности
    names = ["Вахтер_bot", "Призрак_Сессии", "Таракан_Вася", "Сосед_Сверху"]
    name = f"{random.choice(names)}_{bot_id}"
    skin = random.choice(['🤖', '👻', '💀', '👽'])

    @sio.event
    async def connect():
        print(f"[{name}] Подключился к {BACKEND_URL}")
        # Логинимся
        await sio.emit('login', {'password': 'пельмени', 'skin': skin})

    @sio.event
    async def me(data):
        print(f"[{name}] Авторизован. Начинаю жить.")
        # Заходим в коридор случайного этажа
        floor = random.randint(1, 12)
        await sio.emit('join_room', f'floor_{floor}')

        while True:
            # 1. Случайная ходьба
            await sio.emit('move', {'x': random.randint(10, 90), 'y': random.randint(10, 90)})
            
            # 2. Иногда меняем комнату (ходим по этажам)
            if random.random() < 0.05: # 5% шанс сменить этаж
                new_floor = random.randint(1, 12)
                await sio.emit('join_room', f'floor_{new_floor}')
                
            # 3. Иногда спамим реакцию (мусорим)
            if random.random() < 0.02:
                 await sio.emit('interact', {
                     'type': 'add_item', 
                     'payload': {'emoji': '🔩', 'x': random.randint(10,90), 'y': random.randint(10,90)}
                 })

            # Спим рандомно от 2 до 10 секунд
            await asyncio.sleep(random.uniform(2, 10))

    @sio.event
    async def disconnect():
        print(f"[{name}] Отключился. Попробую позже...")

    # Цикл переподключения
    while True:
        try:
            await sio.connect(BACKEND_URL)
            await sio.wait()
        except Exception as e:
            print(f"[{name}] Ошибка подключения: {e}")
            await asyncio.sleep(5) # Ждем перед реконнектом

async def main():
    # Запускаем сразу 5 ботов параллельно
    tasks = []
    for i in range(5):
        tasks.append(run_bot(i))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
