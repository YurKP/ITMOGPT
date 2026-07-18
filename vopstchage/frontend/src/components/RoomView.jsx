import React, { useRef } from 'react';
import { useStore } from '../store/useStore';

export default function RoomView() {
  const { socket, roomUsers, roomItems, roomEnv, currentRoomId, user, setView, hasGem, bossDefeated } = useStore();
  const containerRef = useRef(null);
  
  const isDark = roomEnv.light === "0";
  const isMagicFloor = currentRoomId?.startsWith('-1');
  const isDormStone = currentRoomId === '-1_dorm_stone';

  // Логика типа комнаты
  const getRoomType = (id) => {
      const idStr = String(id).toLowerCase();
      if (idStr.includes('kitchen') || idStr.includes('кухня') || idStr === '0') return 'kitchen';
      if (idStr.includes('study') || idStr.includes('учебка')) return 'study';
      if (idStr.includes('dorm_stone')) return 'dorm_stone';
      return 'dorm'; // Стандартная комната
  };

  const roomType = getRoomType(currentRoomId);

  // Обработка движения
  const handleMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    // Всегда используем socket.emit('move') и updateUserPos
    if (user && user.sid) {
        socket.emit('move', { x, y });
        useStore.getState().updateUserPos(user.sid, x, y);
    }
  };

  const leaveRoom = () => {
      socket.emit('leave_room');
      setView('floor');
  };
  
  // Определяем CSS классы в зависимости от этажа
  const containerClass = isMagicFloor ? 'magic-room-container' : 'room-container';
  const floorClass = isMagicFloor ? 'magic-room-floor' : 'room-floor';
  const windowClass = isMagicFloor ? 'magic-room-window' : 'room-window';

  return (
    <div className={`relative w-full h-[100dvh] select-none overflow-hidden font-mono ${hasGem ? 'gem-holder' : ''}`}>
      
      {/* Header — fixed to prevent disappearing on mobile browser chrome resize */}
      <div className={`fixed top-0 left-0 right-0 z-50 border-b-4 border-black p-4 flex justify-between items-center shadow-md ${isDormStone ? 'bg-red-900 text-white' : 'bg-white'}`}
           style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}>
          <h1 className="text-xl font-bold uppercase tracking-tighter">
            {isDormStone ? '🧟‍♂️ ЛОГОВО ДИПЛОМНИКА' : `ROOM ${currentRoomId}`}
          </h1>
          <div className="flex gap-2">
            <button
                onClick={() => socket.emit('interact', {type: 'toggle_light'})}
                className={`border-2 border-black px-3 py-1 font-bold active:translate-y-1 transition-colors ${isDormStone ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : !isDark ? 'bg-yellow-400' : 'bg-gray-600 text-white'}`}
                title={isDormStone ? 'Кнопка не работает...' : ''}
            >
               {isDark ? '🔦' : '💡'}
            </button>
            <button onClick={leaveRoom} className="bg-red-500 text-white border-2 border-black px-3 py-1 font-bold active:translate-y-1">
               EXIT
            </button>
          </div>
      </div>

      {/* --- ГЛАВНАЯ СЦЕНА --- */}
      <div
           ref={containerRef}
           onClick={handleMove}
           className={`absolute inset-0 w-full overflow-hidden transition-all duration-500 ${isDark ? 'dark-mode cursor-cell' : 'cursor-crosshair'}`}
      >
           
           {/* ДЕКОРАЦИИ: ФОН */}
           <div className={containerClass}>
               {/* Окно */}
               <div className={windowClass}></div>
               
               {/* Пол */}
               <div className={floorClass}></div>

               {/* --- ЛОГИКА МЕБЕЛИ --- */}
               
               {isDormStone ? (
                   <>
                       {!bossDefeated && (
                           <>
                               <div className="boss-eyes"></div>
                               <div className="absolute top-[15%] left-1/2 -translate-x-1/2 text-center z-10 pointer-events-none">
                                   <div className="text-red-500/40 text-[10px] font-bold animate-pulse tracking-widest">
                                       ...шуршание страниц диплома...
                                   </div>
                               </div>
                           </>
                       )}
                       {bossDefeated && (
                           <div className="absolute top-[15%] left-1/2 -translate-x-1/2 text-center z-10 pointer-events-none">
                               <div className="text-green-400/60 text-xs font-bold">
                                   😴 Дипломник спит... Путь свободен!
                               </div>
                           </div>
                       )}
                   </>
               ) : isMagicFloor ? (
                   /* МАГИЧЕСКИЙ ИНТЕРЬЕР */
                   <>
                       <div className="magic-candle" style={{top: '15%', left: '20%', animationDelay: '0s'}}></div>
                       <div className="magic-candle" style={{top: '25%', left: '80%', animationDelay: '1s'}}></div>
                       <div className="magic-candle" style={{top: '10%', left: '50%', animationDelay: '0.5s'}}></div>
                       {/* Котел вместо плиты */}
                       <div className="magic-cauldron"></div>
                   </>
               ) : (
                   /* ОБЫЧНЫЙ ИНТЕРЬЕР */
                   <>
                       {/* Если Кухня: ставим Холодильник + Плиту */}
                       {roomType === 'kitchen' && (
                           <>
                               <div className="room-stove"></div> 
                           </>
                       )}
                       
                       {/* Если Учебка: ставим только Стол */}
                       {roomType === 'study' && (
                           <div className="room-table"></div>
                       )}

                       {/* Если Обычная комната: только Холодильник */}
                       {roomType === 'dorm' && (
                           <div className="room-fridge"></div>
                       )}
                   </>
               )}
           </div>

           {/* Шум (Overlay) */}
           <div className="absolute inset-0 z-0 bg-noise pointer-events-none mix-blend-overlay" />

           {/* ТЕКСТ В ТЕМНОТЕ */}
           {isDark && (
               <div className={`absolute inset-0 pointer-events-none z-1 flex items-center justify-center ${isDormStone ? 'bg-black/80' : 'bg-black/50'}`}>
                   <div className="mt-[250px] animate-pulse">
                       {isDormStone ? (
                           !bossDefeated
                              ? <span className="text-red-500/50 text-xs font-bold tracking-widest">🧟‍♂️ "НЕ ПОДХОДИ... ДЕДЛАЙН ЗАВТРА..."</span>
                              : <span className="text-green-400/50 text-xs font-bold tracking-widest">💎 Что-то блестит на полу...</span>
                       ) : isMagicFloor ? (
                           <span className="text-purple-400/60 text-xs font-bold tracking-widest">Что-то шепчет во тьме...</span>
                       ) : (
                           roomType === 'study'
                              ? <span className="text-white/30 text-xs">тишина...</span>
                              : <span className="text-green-500/40 text-xs font-bold tracking-widest">Холодильник гудит...</span>
                       )}
                   </div>
               </div>
           )}

           {/* --- ИГРОВОЙ СЛОЙ (Предметы) --- */}
           {roomItems.map(item => {
               const safeX = parseFloat(item.x) || 50;
               const safeY = parseFloat(item.y) || 50;
               const isBoss = item.id === 'static_npc_boss';
               const isGem = item.id === 'static_gem_stone';
               return (
                   <div key={item.id}
                        className={`absolute text-5xl transform -translate-x-1/2 -translate-y-1/2 transition-transform cursor-pointer z-10 drop-shadow-xl ${isBoss ? 'boss-npc text-7xl' : isGem ? 'gem-item hover:scale-150' : 'hover:scale-125'}`}
                        style={{
                            left: `${safeX}%`, top: `${safeY}%`,
                            filter: isDark && !isBoss && !isGem ? 'brightness(0.5) sepia(0.3) hue-rotate(180deg)' : 'none'
                        }}
                        onClick={(e) => {
                            e.stopPropagation();
                            // Босс — нельзя кликнуть
                            if (isBoss) return;
                            // Проверяем Кота (NPC)
                            if (item.type === 'npc_cat') {
                                 const wantsPizza = confirm("Покормить кота пиццей? 🍕");
                                 if (wantsPizza) {
                                     socket.emit('interact', { type: 'feed_cat', payload: { item_id: item.id } });
                                 }
                                 return;
                            }
                            if (isGem) {
                                socket.emit('interact', { type: 'remove_item', payload: {id: item.id} });
                                return;
                            }
                            // Обычный предмет - удаляем
                            socket.emit('interact', { type: 'remove_item', payload: {id: item.id} });
                        }}
                   >
                       {item.emoji}
                   </div>
               )
           })}

           {/* --- ИГРОВОЙ СЛОЙ (Игроки) --- */}
           {roomUsers.map(u => {
               const safeX = parseFloat(u.x) || 50;
               const safeY = parseFloat(u.y) || 50;
               const isGemHolder = u.has_gem === "1";
               return (
                   <div key={u.sid}
                        className={`absolute flex flex-col items-center transition-all duration-300 ease-linear z-20 pointer-events-none ${isGemHolder ? 'gem-holder-avatar' : ''}`}
                        style={{left: `${safeX}%`, top: `${safeY}%`, transform: 'translate(-50%, -50%)'}}
                   >
                       <div className="text-5xl drop-shadow-lg relative">
                           {/* Тень под ногами */}
                           <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-8 h-2 bg-black/20 rounded-full blur-sm"></div>
                           {isGemHolder && <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-2xl">👑</span>}
                           {u.skin}
                       </div>
                       <div className={`text-[10px] font-bold px-1 border border-black shadow-sm whitespace-nowrap ${u.sid === user?.sid ? 'bg-yellow-300' : 'bg-white'} ${isGemHolder ? 'gem-nickname' : ''}`}>
                           {u.nickname}
                       </div>
                   </div>
               )
           })}
      </div>

      {/* --- ПАНЕЛЬ ИНСТРУМЕНТОВ --- */}
      <div className={`fixed bottom-0 left-0 right-0 z-50 p-2 border-t-4 border-black flex gap-3 overflow-x-auto justify-start md:justify-center px-4 py-3 shadow-lg pb-[env(safe-area-inset-bottom)] ${isDormStone ? 'bg-red-900/90 border-red-700' : 'bg-[#e5e5e5]'}`}>
          {(isDormStone ? ['🎸', '❤️', '🔮', '✨'] : (hasGem ? ['💰','❤️','🍕','🧦','💩','📦','🪳','🎸', '🅰️', '🅱️'] : ['❤️','🍕','🧦','💩','📦','🪳','🎸', '🅰️', '🅱️'])).map(emoji => (
              <button key={emoji}
                      onClick={(e) => {
                          e.stopPropagation();
                          // Находим актуальные координаты себя
                          const me = roomUsers.find(u => u.sid === user?.sid);
                          const baseX = me ? parseFloat(me.x) : 50;
                          const baseY = me ? parseFloat(me.y) : 50;
                          
                          // Кидаем с разбросом
                          socket.emit('interact', { 
                             type: 'add_item', 
                             payload: { 
                                 emoji, 
                                 x: Math.max(5, Math.min(95, baseX + (Math.random() - 0.5) * 15)), 
                                 y: Math.max(5, Math.min(95, baseY + (Math.random() - 0.5) * 15)) 
                             } 
                          });
                      }}
                      className="text-3xl border-2 border-black bg-white min-w-[3.5rem] h-14 flex-shrink-0 active:bg-gray-300 active:scale-95 transition-transform rounded-sm shadow-[3px_3px_0_0_rgba(0,0,0,1)] active:shadow-none flex items-center justify-center">
                  {emoji}
              </button>
          ))}
          <div className="w-2 flex-shrink-0"></div>
      </div>
    </div>
  )
}
