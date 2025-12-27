import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ""),
                ws: true,
            },
        },
    },
    build: {
        // Code splitting configuration
        rollupOptions: {
            output: {
                manualChunks: {
                    // Vendor chunks
                    'react-vendor': ['react', 'react-dom', 'react-router-dom'],
                    'chart-vendor': ['chart.js', 'react-chartjs-2'],
                    'ui-vendor': ['framer-motion', 'lucide-react'],
                },
            },
        },
        // Optimize chunk size
        chunkSizeWarningLimit: 1000,
        // Enable source maps for production debugging (optional)
        sourcemap: false,
    },
    // Optimize dependencies
    optimizeDeps: {
        include: [
            'react',
            'react-dom',
            'react-router-dom',
            'chart.js',
            'react-chartjs-2',
            'framer-motion',
            'lucide-react',
        ],
    },
})
