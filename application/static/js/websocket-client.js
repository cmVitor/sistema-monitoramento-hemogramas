/**
 * WebSocket client - Handles real-time communication
 */

import { CONFIG } from './config.js';

export class WebSocketClient {
    constructor(onMessage) {
        this.onMessage = onMessage;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.heartbeatInterval = null;
        this.isConnected = false;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${CONFIG.API.websocket}`;

        console.log('Connecting to WebSocket...');
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => this.handleOpen();
        this.ws.onmessage = (event) => this.handleMessage(event);
        this.ws.onerror = (error) => this.handleError(error);
        this.ws.onclose = () => this.handleClose();
    }

    /**
     * Handle WebSocket open
     */
    handleOpen() {
        console.log('✓ WebSocket connected - real-time updates active');
        this.isConnected = true;
        this.reconnectAttempts = 0;

        // Send heartbeat every 25 seconds
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }, CONFIG.WEBSOCKET.heartbeatInterval);
    }

    /**
     * Handle WebSocket message
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('WebSocket message received:', message.type);

            // Handle ping
            if (message.type === 'ping') {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'pong' }));
                }
                return;
            }

            // Notify callback
            if (this.onMessage) {
                this.onMessage(message);
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    }

    /**
     * Handle WebSocket error
     */
    handleError(error) {
        console.error('WebSocket error:', error);
    }

    /**
     * Handle WebSocket close
     */
    handleClose() {
        console.log('WebSocket connection closed');
        this.isConnected = false;

        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        // Attempt to reconnect with exponential backoff
        if (this.reconnectAttempts < CONFIG.WEBSOCKET.reconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(
                CONFIG.WEBSOCKET.reconnectDelay * Math.pow(1.5, this.reconnectAttempts),
                30000
            );
            console.log(`Reconnecting in ${delay/1000}s... (attempt ${this.reconnectAttempts}/${CONFIG.WEBSOCKET.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.warn('Max reconnection attempts reached. Using polling fallback.');
        }
    }

    /**
     * Check if connected
     */
    isConnectedToServer() {
        return this.isConnected;
    }

    /**
     * Disconnect
     */
    disconnect() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        if (this.ws) {
            this.ws.close();
        }
    }
}
