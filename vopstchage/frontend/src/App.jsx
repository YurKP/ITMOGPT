import React, { useEffect } from 'react';
import io from 'socket.io-client';
import { useStore } from './store/useStore';
import { loadSession, saveSession, clearSession } from './store/useStore';
import RoomView from './components/RoomView';
import MapView from './components/MapView';
import FloorView from './components/FloorView';
import LoginView from './components/LoginView';

export default function App() {
  const { setSocket, setUser, setRoomState, addUser, removeUser, updateUserPos, addItem, removeItem, setLight, setView, view, addNotification } = useStore();

  useEffect(() => {
    const newSocket = io(import.meta.env.VITE_API_URL || '/', {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
    });
    
    setSocket(newSocket);

    newSocket.on('connect', () => {
      // Пробуем восстановить сессию из localStorage
      const cached = loadSession();
      if (cached && cached.token) {
        newSocket.emit('restore_session', { token: cached.token }, (response) => {
          if (response && response.status === 'ok') {
            // Проверяем, был ли пользователь в комнате/на этаже до реконнекта
            const state = useStore.getState();
            const currentView = state.view;
            const currentRoomId = state.currentRoomId;
            
            if (currentView === 'room' && currentRoomId) {
              // Пользователь был в комнате — переподключаемся к ней
              newSocket.emit('join_room', currentRoomId);
            } else if (currentView === 'floor') {
              // Пользователь был на этаже — переподключаемся к коридору
              const corridorId = `floor_${state.currentFloor}`;
              newSocket.emit('join_room', corridorId);
            } else {
              // Первый вход или был на карте — идем на карту
              setView('map');
            }
          } else {
            // Токен протух или невалиден — чистим и показываем логин
            clearSession();
            setView('login');
          }
        });
      } else {
        // Нет сохраненной сессии — показываем логин
        setView('login');
      }
    });

    newSocket.on('me', (data) => {
        if (data.unlocked_basement === "1") {
              useStore.getState().unlockFloor(-1);
        }
        if (data.has_gem === "1") {
              useStore.getState().setHasGem(true);
        }
        if (data.faculty) {
              useStore.getState().setFaculty(data.faculty);
        }
        setUser(data);
        
        // Сохраняем/обновляем сессию в localStorage при каждом "me"
        if (data.token) {
          saveSession(data.token, data.nickname, data.skin);
        }
    });
    
    // Room events
    newSocket.on('room_state', (data) => setRoomState(data));
    newSocket.on('user_joined', (u) => addUser(u));
    newSocket.on('user_left', ({sid}) => removeUser(sid));
    newSocket.on('user_moved', ({sid, x, y}) => updateUserPos(sid, x, y));
    newSocket.on('item_added', (item) => addItem(item));
    newSocket.on('item_removed', (id) => removeItem(id));
    newSocket.on('light_update', (isOn) => setLight(isOn));
    newSocket.on('achievement_unlocked', (data) => {
      if (data.id === 'basement') {
          useStore.getState().unlockFloor(-1);
          alert("ВЫ НАШЛИ КЛЮЧ ОТ ПОДВАЛА!");
      }
    });

    newSocket.on('sorting_hat_result', (data) => {
        useStore.getState().setFaculty(data.faculty);
        // Обновляем user nickname локально
        const state = useStore.getState();
        if (state.user) {
            setUser({ ...state.user, nickname: data.new_nickname });
        }
        alert(`🎩 Распределяющая Шляпа кричит:\n\n${data.emoji} ${data.faculty.toUpperCase()}!\n\n"${data.desc}"\n\nТвой новый ник: ${data.new_nickname}`);
    });

    newSocket.on('user_nickname_changed', ({sid, nickname}) => {
        useStore.getState().updateUserNickname(sid, nickname);
    });

    newSocket.on('boss_teleport', (data) => {
        alert(data.msg);
        useStore.getState().setCurrentFloor(1);
        useStore.getState().setView('floor');
        const corridorId = 'floor_1';
        newSocket.emit('join_room', corridorId);
    });

    newSocket.on('boss_defeated', () => {
        useStore.getState().setBossDefeated(true);
    });

    newSocket.on('gem_collected', () => {
        useStore.getState().setHasGem(true);
        alert("💎 ТЫ ДОБЫЛ ОБЩАЖНЫЙ КАМЕНЬ!\n\n✨ Теперь у тебя золотое свечение!\n💰 Все твои предметы на обычных этажах — золото!");
    });

    newSocket.on('notification', (msg) => {
        useStore.getState().addNotification(msg);
        // Автоудаление через 5 секунд
        setTimeout(() => {
            useStore.getState().clearNotification(0);
        }, 5000);
    });

    newSocket.on('global_stats', (stats) => {
        useStore.getState().setGlobalStats(stats);
    });

    return () => newSocket.disconnect();
  }, []);

  const notifications = useStore((s) => s.notifications);

  return (
    <div className="w-full h-[100dvh] bg-[#e0e0e0] font-mono text-black overflow-hidden select-none">
       {view === 'loading' && (
         <div className="h-full flex items-center justify-center bg-[#edeef0]">
           <div className="text-center">
             <div className="text-6xl mb-4 animate-bounce">🏠</div>
             <div className="font-bold text-lg">Загружаем общагу...</div>
           </div>
         </div>
       )}
       {view === 'login' && <LoginView />}
       {view === 'map' && <MapView />}
       {view === 'room' && <RoomView />}
       {view === 'floor' && <FloorView />}

       {/* Глобальные уведомления (Toast) */}
       <div className="fixed top-16 left-1/2 -translate-x-1/2 z-[999] flex flex-col gap-2 pointer-events-none">
         {notifications.map((msg, i) => (
           <div key={i} className="notification-toast bg-black/90 text-white px-4 py-2 border-2 border-yellow-400 text-sm font-bold text-center max-w-[90vw] shadow-lg animate-slide-down">
             {msg}
           </div>
         ))}
       </div>
    </div>
  );
}
