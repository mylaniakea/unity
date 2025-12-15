import { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface TerminalProps {
    profileId: number;
    onClose: () => void;
}

export default function Terminal({ profileId, onClose }: TerminalProps) {
    const terminalRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const xtermRef = useRef<XTerm | null>(null);

    useEffect(() => {
        if (!terminalRef.current) return;

        // Initialize xterm.js
        const term = new XTerm({
            cursorBlink: true,
            theme: {
                background: '#1a1b26',
                foreground: '#c0caf5',
            },
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
            fontSize: 14,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(terminalRef.current);
        fitAddon.fit();
        
        // Ensure focus after a brief delay to allow modal animation
        setTimeout(() => term.focus(), 100);
        
        xtermRef.current = term;

        // Connect WebSocket
        // Determine WS protocol (ws or wss) based on current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // If dev mode (port 5173), assume backend on 8000. If prod (nginx), path is /api/terminal
        // But our backend path is /terminal/ws/...
        // We need to match the proxy config.
        // Vite proxy rewrites /api -> http://backend:8000
        // So we should connect to /api/terminal/ws/{id} if proxy handles upgrades.
        // Nginx typically needs special config for websockets.
        
        // For local dev, hardcode localhost:8000 if needed, or use relative path if proxy supports it.
        // Let's try relative path assuming Nginx/Vite proxy handles it.
        // The backend router prefix is /terminal, so path is /terminal/ws/{id}
        // If we go through /api, it maps to backend root.
        
        const wsUrl = `${protocol}//${window.location.host}/api/terminal/ws/${profileId}`;
        console.log(`Connecting to Terminal WS: ${wsUrl}`);
        
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            term.write('\r\n\x1b[32m[Homelab Intelligence] Connecting to SSH...\x1b[0m\r\n');
            
            // Send initial resize
            const dims = { cols: term.cols, rows: term.rows };
            ws.send(JSON.stringify(dims));
            term.focus();
        };

        ws.onmessage = (event) => {
            term.write(event.data);
        };

        ws.onclose = (ev) => {
            term.write(`\r\n\x1b[31m[Homelab Intelligence] Connection closed (Code: ${ev.code}).\x1b[0m\r\n`);
        };

        ws.onerror = (err) => {
            console.error("WS Error", err);
            term.write('\r\n\x1b[31m[Homelab Intelligence] WebSocket Error.\x1b[0m\r\n');
        };

        // Handle user input
        term.onData((data) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(data);
            }
        });

        // Handle resize
        const handleResize = () => {
            fitAddon.fit();
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ cols: term.cols, rows: term.rows }));
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            console.log("Cleaning up terminal");
            window.removeEventListener('resize', handleResize);
            ws.close();
            term.dispose();
        };
    }, [profileId]);

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-[#1a1b26] border border-gray-700 rounded-lg shadow-2xl w-full max-w-5xl h-[80vh] flex flex-col overflow-hidden">
                <div className="flex justify-between items-center px-4 py-2 bg-gray-900 border-b border-gray-700">
                    <span className="text-sm font-mono text-gray-400">Terminal - Session #{profileId}</span>
                    <button 
                        onClick={onClose}
                        className="text-gray-400 hover:text-white hover:bg-red-500/20 px-2 py-1 rounded transition-colors"
                    >
                        Close
                    </button>
                </div>
                <div className="flex-grow p-2 overflow-hidden" ref={terminalRef} />
            </div>
        </div>
    );
}
