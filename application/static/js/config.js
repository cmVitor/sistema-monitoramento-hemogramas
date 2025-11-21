/**
 * Configuration and constants
 */

export const CONFIG = {
    // Map configuration
    MAP: {
        center: [-14.235, -51.925],
        zoom: 4,
        tileLayer: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        maxZoom: 18
    },

    // Color scheme for intensity levels
    COLORS: {
        low: '#22c55e',      // Verde - Normal
        normal: '#eab308',   // Amarelo - Atenção
        high: '#f97316',     // Laranja - Alto
        critical: '#dc2626', // Vermelho - Crítico
        outbreak: '#7c2d12'  // Marrom escuro - Surto
    },

    // Thresholds for leukocyte levels
    THRESHOLDS: {
        low: 5000,
        normal: 10000,
        high: 15000
    },

    // WebSocket configuration
    WEBSOCKET: {
        reconnectAttempts: 10,
        reconnectDelay: 1000,
        heartbeatInterval: 25000,
        timeout: 30000
    },

    // Polling configuration (fallback)
    POLLING: {
        interval: 60000  // 60 seconds
    },

    // API endpoints
    API: {
        heatmapData: '/heatmap-data',
        seedData: '/seed-data',
        websocket: '/ws'
    }
};
