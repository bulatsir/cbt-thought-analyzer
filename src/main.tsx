// Импорт React-компонентов из библиотеки (аналог from react import StrictMode)
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Импорт CSS — Vite подхватывает и вставляет стили на страницу
import './index.css'
// default-экспорт можно импортировать без фигурных скобок
import App from './App'

// document.getElementById('root')! — восклицательный знак говорит TypeScript:
// "я уверен, что элемент существует, не ругайся на возможный null"
createRoot(document.getElementById('root')!).render(
  // JSX: HTML-подобный синтаксис прямо в JS. <App /> — вызов React-компонента
  <StrictMode>
    <App />
  </StrictMode>,
)
