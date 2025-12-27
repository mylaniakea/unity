import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
    <App />
)

// Register service worker (disabled for now to prevent browser freezing)
// if ('serviceWorker' in navigator) {
//     window.addEventListener('load', () => {
//         navigator.serviceWorker.register('/service-worker.js')
//             .then(registration => {
//                 console.log('Service Worker registered: ', registration);
//             })
//             .catch(error => {
//                 console.error('Service Worker registration failed: ', error);
//             });
//     });
// }
