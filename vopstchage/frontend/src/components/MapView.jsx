import React from 'react';
import { useStore } from '../store/useStore';

export default function MapView() {
  const { setView, setCurrentFloor, globalStats, user, unlockedFloors } = useStore();
  const {  } = useStore();
  
  // Создаем массив этажей [12, 11, ..., 1]
  const floors = Array.from({ length: 12 }, (_, i) => 12 - i);
  if (unlockedFloors.includes(-1)) {
      floors.push(-1); // Добавляем ПОДВАЛ в конец списка
  }

  const handleSelectFloor = (floorNum) => {
    setCurrentFloor(floorNum);
    setView('floor'); // Переходим к виду коридора
  };

  return (
    <div className="h-full flex flex-col bg-gray-200">
      {/* Заголовок */}
      {/* Заголовок (Header) */}
      <div className="p-4 border-b-4 border-black bg-white brutal-shadow z-10 flex justify-between items-center sticky top-0">
        
        {/* Левая часть: Название */}
        <div>
          <h1 className="text-2xl font-bold uppercase tracking-tighter leading-none">ВОБЩАГЕ</h1>
          <p className="text-xs font-mono text-gray-500">Выбери этаж...</p>
        </div>

        {/* Правая часть: Профиль игрока */}
        <div className="flex items-center gap-2 pl-4 border-l-2 border-black border-dashed">
            <div className="text-right hidden sm:block"> {/* На совсем мелких экранах ник скроем, оставим лицо */}
                <span className="block text-[10px] font-bold bg-yellow-300 border border-black px-1 mb-0.5">YOU</span>
                <span className="block text-xs font-mono max-w-[100px] truncate">{user?.nickname}</span>
            </div>
            
            {/* Смайл */}
            <div className="text-4xl filter drop-shadow-md cursor-help hover:scale-110 transition-transform" title={user?.nickname}>
                {user?.skin || '😐'}
            </div>
        </div>
      </div>

      {/* Список этажей (Скролл) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {floors.map((floor) => {
          // Данные по этажу (берем из globalStats, если есть)
          // Пример структуры stats: { "5": { count: 10, has_fire: true } }
          const stats = globalStats?.[floor] || { count: 0, has_fire: false };
          
          return (
            <div 
              key={floor}
              onClick={() => handleSelectFloor(floor)}
              className="brutal-box p-4 flex items-center justify-between cursor-pointer hover:bg-yellow-200 active:bg-yellow-300 transition-colors"
            >
              {/* Номер этажа */}
              <div className="flex items-center gap-4">
                <div className="text-4xl font-black w-12 text-center border-r-4 border-black pr-4">
                  {floor}
                </div>
                <div>
                  <div className="font-bold text-lg">ЭТАЖ {floor}</div>
                  <div className="text-xs text-gray-600 font-mono">
                    {stats.count > 0 ? `Users: ${stats.count}` : 'Empty'}
                  </div>
                </div>
              </div>

              {/* Индикаторы хаоса */}
              <div className="text-2xl flex gap-2">
                {stats.has_fire && <span className="animate-bounce">🔥</span>}
                {stats.count > 5 && <span>🔊</span>} 
                {/* Если ничего нет - показываем стрелку */}
                {!stats.has_fire && stats.count <= 5 && <span className="opacity-20">➜</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Футер */}
      <div className="p-2 text-center text-[10px] opacity-50 font-mono">
        FROM OPSHAGA WITH LOVE
      </div>
    </div>
  );
}
