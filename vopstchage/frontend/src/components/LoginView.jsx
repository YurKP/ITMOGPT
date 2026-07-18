import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { saveSession } from '../store/useStore';

export default function LoginView() {
  const { socket } = useStore();
  const [password, setPassword] = useState('');
  const [selectedSkin, setSkin] = useState('😐');
  const [error, setError] = useState(null);

  const skins = ['😐','🤡','💀','👽','👺','🤖','👻'];

  const handleLogin = () => {
    if (!socket) return;
    
    socket.emit('login', { password, skin: selectedSkin }, (response) => {
        if (response.status === 'ok') {
            // Токен также придет через событие "me" и сохранится в App.jsx,
            // но на всякий случай сохраняем и из callback
            if (response.token) {
              saveSession(response.token, '', selectedSkin);
            }
            useStore.getState().setView('map'); // Пускаем внутрь
        } else {
            setError(response.msg);
        }
    });
  };

  return (
    <div className="h-full flex flex-col items-center justify-center bg-[#edeef0] text-black">
       {/* ЛОГОТИП CSS-Parody */}
       <div className="mb-8 flex flex-col items-center gap-2">
           <div className="flex items-center gap-2">
               {/* Иконка "В" в квадрате */}
               <div className="w-16 h-16 bg-[#0077FF] border-4 border-black box-shadow-brutal flex items-center justify-center rounded-lg transform -rotate-6">
                   <span className="text-white font-black text-4xl mt-1">В</span>
               </div>
               {/* Текст */}
               <div className="font-black text-4xl uppercase tracking-tighter">
                   Общаге
               </div>
           </div>
           
           <div className="text-xs font-mono bg-yellow-300 px-2 border border-black transform rotate-2">
             тараканы included 🪳🪳
           </div>
       </div>

       {/* ФОРМА ВХОДА */}
       <div className="bg-white border-4 border-black p-6 brutal-shadow w-80 flex flex-col gap-4">
           
           <div className="text-center font-bold">ВХОД ТОЛЬКО ДЛЯ ЖИЛЬЦОВ</div>
           
           {/* Вопрос */}
           <div className="text-sm">
               ЗАГАДКА: Лучшая общага в мире (а также милый зверек)?
           </div>
           
           <input 
              type="text" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Ответ..."
              className="border-2 border-black p-2 font-mono uppercase focus:bg-yellow-100 outline-none"
           />
           
           {/* Выбор скина */}
           <div className="text-sm">ТВОЕ ЛИЦО СЕГОДНЯ:</div>
           <div className="flex flex-wrap gap-2 justify-center p-2">
                {skins.map(s => (
                    <button key={s} onClick={() => setSkin(s)}
                            // ИЗМЕНЕНИЕ ЗДЕСЬ:
                            className={`text-2xl border-2 border-black w-10 h-10 flex items-center justify-center transition-all duration-200
                            $${selectedSkin === s 
                                ? 'bg-[#0077FF] scale-125 ring-2 ring-offset-2 ring-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] z-10' 
                                : 'bg-white hover:bg-gray-200 hover:scale-110'
                            }`}
                    >
                        {s}
                    </button>
                ))}
            </div>

           {error && <div className="text-red-600 font-bold text-center animate-pulse">{error}</div>}

           <button onClick={handleLogin} className="bg-[#0077FF] text-white font-black py-3 border-2 border-black hover:translate-y-1 active:translate-y-2 transition-transform brutal-shadow">
               ВОЙТИ
           </button>
       </div>
    </div>
  );
}
