/**
 * Main application entry point
 */

import { CONFIG } from './config.js';
import { MapManager } from './map-manager.js';
import { FilterManager } from './filter-manager.js';
import { StatisticsManager } from './statistics-manager.js';
import { WebSocketClient } from './websocket-client.js';
import { DataGenerator } from './data-generator.js';
import { UIUtils } from './ui-utils.js';

class HemogramMonitoringApp {
    constructor() {
        this.mapManager = null;
        this.filterManager = null;
        this.statisticsManager = null;
        this.websocketClient = null;
        this.dataGenerator = null;
        this.pollingInterval = null;
    }

    /**
     * Initialize application
     */
    async initialize() {
        console.log('🚀 Initializing Hemogram Monitoring System...');

        // Initialize managers
        this.mapManager = new MapManager();
        this.mapManager.initialize();

        this.filterManager = new FilterManager((filter) => {
            this.mapManager.setFilter(filter);
        });
        this.filterManager.initialize();

        this.statisticsManager = new StatisticsManager();

        this.dataGenerator = new DataGenerator((status, data) => {
            if (status === 'generated') {
                this.loadHeatmapData();
            }
        });
        this.dataGenerator.initialize();

        // Request notification permission
        await UIUtils.requestNotificationPermission();

        // Load initial data
        await this.loadHeatmapData();

        // Initialize WebSocket
        this.websocketClient = new WebSocketClient((message) => {
            this.handleWebSocketMessage(message);
        });
        this.websocketClient.connect();

        // Setup polling fallback
        this.setupPollingFallback();

        console.log('✓ Application initialized successfully');
    }

    /**
     * Load heatmap data from API
     */
    async loadHeatmapData() {
        try {
            const response = await fetch(CONFIG.API.heatmapData);
            const data = await response.json();

            // Update map
            this.mapManager.setData(data.observations || [], data.outbreaks || {});

            // Update statistics
            this.statisticsManager.update(data.observations || []);

            console.log(`Loaded ${data.observations?.length || 0} points for map`);
        } catch (error) {
            console.error('Error loading heatmap data:', error);
        }
    }

    /**
     * Handle WebSocket message
     */
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'new_observation':
                console.log('New observation received:', message.data);
                this.loadHeatmapData();
                break;

            case 'outbreak_alert':
                console.warn('⚠️ OUTBREAK ALERT:', message.data);
                UIUtils.showNotification(
                    'Alerta de Surto Detectado!',
                    `Região: ${message.data.region}\n${message.data.summary}`
                );
                this.loadHeatmapData();
                break;

            case 'refresh_data':
                console.log('Data refresh requested');
                this.loadHeatmapData();
                break;

            default:
                console.log('Unknown message type:', message.type);
        }
    }

    /**
     * Setup polling fallback for when WebSocket is not connected
     */
    setupPollingFallback() {
        this.pollingInterval = setInterval(() => {
            if (!this.websocketClient.isConnectedToServer()) {
                console.log('WebSocket not connected, using polling fallback');
                this.loadHeatmapData();
            }
        }, CONFIG.POLLING.interval);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new HemogramMonitoringApp();
    app.initialize();
});
