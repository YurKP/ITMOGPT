import React, { useEffect, useRef, useMemo, useLayoutEffect } from 'react';
import { useStore } from '../store/useStore';

export default function FloorView() {
  const { currentFloor, setView, socket, roomUsers, roomItems, user, lastEnteredRoom, hasGem } = useStore();
  
  // Ref вешаем на ВНУТРЕННИЙ контент, чтобы считать координаты
  const contentRef = useRef(null);
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    const corridorId = `floor_${currentFloor}`;
    socket.emit('join_room', corridorId);
    
    // Мгновенный сброс в центр
    useStore.getState().updateUserPos(user?.sid, 50, 50);
    socket.emit('move', { x: 50, y: 50 });
  }, [currentFloor, socket, user?.sid]);

  // Скролл к последней посещённой комнате при возврате из неё
  useLayoutEffect(() => {
    if (!lastEnteredRoom || !scrollContainerRef.current) return;
    
    // Ищем кнопку комнаты по data-атрибуту
    const roomBtn = scrollContainerRef.current.querySelector(`[data-room-suffix="${lastEnteredRoom}"]`);
    if (roomBtn) {
      // Скроллим к комнате с небольшим отступом сверху
      roomBtn.scrollIntoView({ block: 'center', behavior: 'instant' });
    }
  }, [lastEnteredRoom]);

  // КОНФИГУРАЦИЯ ЭТАЖЕЙ
  const floorConfig = useMemo(() => {
    const standardLeft = [2, 4, 'KITCHEN_1', 'LIFT', 6, 8, 'UCHEBKA_1', 'UCHEBKA_2', 10, 12, 'LIFT', 'KITCHEN_2', 14, 16];
    const standardRight = [1, 3, 5, 7, 9, 'UCHEBKA_3', 'UCHEBKA_4', 11, 13, 15, 17, 19];

    if (currentFloor === 1) {
        return {
            left: standardLeft, 
            right: [1, 3, 5, 7, 9, 'POST_OHRANA', 'TURNIQUET', 11, 13, 15, 17, 19]
        };
    }
    
    if (currentFloor === -1) {
        return {
            left: ['SORTING_HAT', 'DORM_STONE'],
            right: ['LIFT']
        };
    }
    
    return { left: standardLeft, right: standardRight };
  }, [currentFloor]);

  // ОБРАБОТЧИК ХОДЬБЫ
  const handleWalk = (e) => {
      if (e.target.closest('.room-btn') || e.target.closest('.interactive-item') || e.target.closest('button')) return;
      
      const content = contentRef.current;
      if (!content) return;

      const rect = content.getBoundingClientRect();
      const relativeX = e.clientX - rect.left;
      const relativeY = e.clientY - rect.top;

      let x = (relativeX / rect.width) * 100;
      let y = (relativeY / rect.height) * 100;

      x = Math.max(0, Math.min(100, x));
      y = Math.max(0, Math.min(100, y));

      socket.emit('move', { x, y });
      useStore.getState().updateUserPos(user?.sid, x, y);
  };

  const enterRoom = (roomSuffix) => {
    const roomId = `${currentFloor}_${roomSuffix}`;
    useStore.getState().setLastEnteredRoom(roomSuffix);
    socket.emit('join_room', roomId);
    setView('room');
  };

  const goBackToMap = () => {
    setView('map');
  };

  const renderCell = (item, side, index) => {
    const key = `${side}-${index}-${item}`;

    if (item === 'DORM_STONE') {
        return (
            <div key={key} data-room-suffix="dorm_stone" onClick={() => enterRoom('dorm_stone')}
                 className="room-btn w-full h-28 bg-red-900 border-4 border-yellow-500 flex flex-col items-center justify-center shadow-lg mb-2 z-10 relative cursor-pointer hover:bg-red-800 transition-colors dorm-stone-btn">
                <span className="text-4xl animate-pulse">🧟‍♂️</span>
                <span className="font-bold text-xs text-yellow-200 mt-1">ОБЩАЖНЫЙ КАМЕНЬ</span>
                <span className="text-[9px] text-red-300 mt-0.5">⚠️ Бессонный Дипломник</span>
            </div>
        );
    }
    if (item === 'SORTING_HAT') {
        return (
            <div key={key}
                 onClick={() => {
                     socket.emit('interact', { type: 'sorting_hat' });
                 }}
                 className="room-btn w-full h-28 bg-purple-900 border-4 border-yellow-600 flex flex-col items-center justify-center cursor-pointer hover:bg-purple-700 shadow-lg mb-2 z-10 relative transition-all sorting-hat-btn">
                <span className="text-4xl sorting-hat-icon">🎩</span>
                <span className="font-bold text-sm text-yellow-200 mt-1">РАСПРЕДЕЛЯЮЩАЯ ШЛЯПА</span>
                <span className="text-[9px] text-purple-300">Узнай свой факультет!</span>
            </div>
        );
    }

    // --- ОБЫЧНЫЕ КОМНАТЫ ---
    if (item === 'POST_OHRANA') {
        return (
            <div key={key} onClick={() => alert("ПРЕДЪЯВИТЕ ПРОПУСК!")}
                className="room-btn w-full h-10 bg-blue-900 border-4 border-black flex flex-col items-center justify-center cursor-help shadow-lg mb-2 z-10 relative text-white">
                <span className="text-3xl">👮‍♂️</span>
                <span className="font-bold text-xs mt-1">ОХРАНА</span>
            </div>
        );
    }
    if (item === 'TURNIQUET' || ((typeof item === 'string') && item.startsWith('UCHEBKA'))) {
         return (
            <div key={key} data-room-suffix={item.startsWith?.('UCHEBKA') ? item.toLowerCase() : undefined}
                onClick={item.startsWith('UCHEBKA') ? () => enterRoom(item.toLowerCase()) : undefined}
                className="room-btn w-full h-10 bg-gray-300 border-2 border-dashed border-black flex items-center justify-center mb-2 opacity-70">
                <span className="font-mono text-xs font-bold">{item.startsWith('UCHEBKA') ? 'УЧЕБКА' : 'ТУРНИКЕТ'}</span>
            </div>
         );
    }
    if ((typeof item === 'string') && item.startsWith('KITCHEN')) {
        return (
            <div key={key} data-room-suffix={item.toLowerCase()} onClick={() => enterRoom(item.toLowerCase())}
                className="room-btn w-full h-10 bg-yellow-300 border-2 border-black flex items-center justify-center cursor-pointer hover:bg-yellow-400 brutal-shadow mb-2 z-10 relative">
                <span className="font-bold">КУХНЯ</span>
            </div>
        );
    }
    if (item === 'LIFT') {
      return (
        <div key={key} onClick={goBackToMap}
             className="room-btn w-full h-20 bg-gray-400 border-2 border-black flex items-center justify-center cursor-pointer hover:bg-gray-500 brutal-shadow my-2 z-10 relative">
           <span className="font-bold text-white">ЛИФТ</span>
        </div>
      );
    }
    
    // Номерные комнаты
    const roomNum = `${currentFloor}${item.toString().padStart(2, '0')}`;
    // Мелкие комнаты (для разнообразия сетки)
    if ((item === 6) || (item === 12)) {
      return (
        <div key={key} data-room-suffix={roomNum} onClick={() => enterRoom(roomNum)}
          className="room-btn w-full h-10 bg-white border-2 border-black flex flex-col items-center justify-center cursor-pointer hover:bg-blue-200 active:scale-95 transition-all brutal-shadow mb-2 z-10 relative">
          <span className="font-bold text-lg">{roomNum}</span>
        </div>
      );
    }

    return (
      <div key={key} data-room-suffix={roomNum} onClick={() => enterRoom(roomNum)}
        className="room-btn w-full h-20 bg-white border-2 border-black flex flex-col items-center justify-center cursor-pointer hover:bg-blue-200 active:scale-95 transition-all brutal-shadow mb-2 z-10 relative">
        <span className="font-bold text-lg">{roomNum}</span>
      </div>
    );
  };

  // Фон меняется для подземелья
  const bgClass = currentFloor === -1 ? 'bg-zinc-900' : 'bg-gray-100';

  return (
    <div className={`h-full flex flex-col ${bgClass}`}>
      {/* 1. ШАПКА — fixed to prevent disappearing on mobile */}
      <div className={`fixed top-0 left-0 right-0 p-4 flex gap-4 border-b-4 border-black z-20 shadow-md ${currentFloor === -1 ? 'bg-purple-900 text-white' : 'bg-white'}`}
           style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}>
        <div className="flex-1 text-center font-bold text-2xl pt-1">
          {currentFloor === 1 ? "ВАХТА / ХОЛЛ" : currentFloor === -1 ? "ПОДЗЕМЕЛЬЕ" : `КОРИДОР ${currentFloor}`}
        </div>
      </div>

      {/* 2. ОКНО ПРОСМОТРА С SCROLL — с отступом сверху под fixed header */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto custom-scrollbar mt-[60px]">
          
          {/* 3. КОНТЕНТ (Относительный) */}
          <div 
            ref={contentRef} 
            onClick={handleWalk} 
            className="relative p-4 min-h-full pb-32" 
          >
            
            {/* ПРЕДМЕТЫ */}
            {roomItems.map(item => {
               const safeX = parseFloat(item.x) || 50; 
               const safeY = parseFloat(item.y) || 50;
               return (
                 <div key={item.id} 
                      className="interactive-item absolute text-3xl transform -translate-x-1/2 -translate-y-1/2 z-20 cursor-pointer hover:scale-125 transition-transform"
                      style={{left: `${safeX}%`, top: `${safeY}%`}}
                      onClick={(e) => {
                          e.stopPropagation();
                          socket.emit('interact', { type: 'remove_item', payload: {id: item.id} });
                      }}
                 >
                    {item.emoji}
                 </div>
               )
            })}

            {/* ПЕРСОНАЖИ */}
            {roomUsers.map(u => {
               const safeX = parseFloat(u.x) || 50;
               const safeY = parseFloat(u.y) || 50;
               const isMe = u.sid === user?.sid;
               return (
                 <div key={u.sid} 
                      className="absolute flex flex-col items-center pointer-events-none z-30 transition-all duration-300 linear"
                      style={{left: `${safeX}%`, top: `${safeY}%`, transform: 'translate(-50%, -50%)'}}
                 >
                    <div className="text-4xl drop-shadow-md avatar-float">{u.skin}</div>
                    <div className={`text-[10px] border border-black px-1 shadow-sm whitespace-nowrap ${isMe ? 'bg-yellow-300 font-bold' : 'bg-white'}`}>
                        {u.nickname}
                    </div>
                 </div>
               )
            })}

            {/* СЕТКА КОМНАТ */}
            <div className="flex justify-between gap-8">
              <div className="flex-1 flex flex-col pt-4 space-y-2">
                {floorConfig.left.map((item, idx) => renderCell(item, 'left', idx))}
              </div>

              {/* Декор по центру (исчезает в подвале) */}
              <div className="w-16 flex flex-col items-center opacity-30 pointer-events-none" 
                   style={currentFloor !== -1 ? {backgroundImage: 'radial-gradient(circle, #000 1px, transparent 1px)', backgroundSize: '20px 20px'} : {}}>
              </div>

              <div className="flex-1 flex flex-col pt-4 space-y-2">
                {floorConfig.right.map((item, idx) => renderCell(item, 'right', idx))}
              </div>
            </div>
          </div>
      </div>

      {/* 4. ПАНЕЛЬ ЭМОДЗИ */}
      <div className={`fixed bottom-0 left-0 right-0 p-2 border-t-4 border-black z-50 flex gap-2 overflow-x-auto justify-center shadow-lg safe-area-bottom ${currentFloor === -1 ? 'bg-purple-900 border-purple-400' : 'bg-gray-100'}`}>
          {(currentFloor === -1 ? ['❤️', '🔮', '🪄', '🎩', '🎸', '✨'] : (hasGem ? ['💰','❤️','🍕','🧦','💩','📦','🎸', '🐀'] : ['❤️','🍕','🧦','💩','📦','🎸', '🐀'])).map(emoji => (
              <button key={emoji} 
                      className="text-2xl border-2 border-black bg-white w-12 h-12 flex-shrink-0 active:bg-gray-200 hover:-translate-y-1 transition-transform shadow-sm"
                      onClick={(e) => {
                          e.stopPropagation();
                          const me = roomUsers.find(u => u.sid === user?.sid);
                          const currentX = parseFloat(me?.x) || 50;
                          const currentY = parseFloat(me?.y) || 50;
                          
                          socket.emit('interact', { 
                             type: 'add_item', 
                             payload: { 
                                 emoji, 
                                 x: currentX + (Math.random() - 0.5) * 5, 
                                 y: currentY + (Math.random() - 0.5) * 5 
                             } 
                          });
                      }}
              >
                  {emoji}
              </button>
          ))}
      </div>
    </div>
  );
}
