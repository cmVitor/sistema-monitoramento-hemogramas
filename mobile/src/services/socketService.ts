import { io, Socket } from 'socket.io-client';
import { API_BASE_URL } from '../config';
import { getDeviceId } from '../utils/device';

/**
 * Socket.IO Service para comunicação em tempo real.
 *
 * Gerencia conexão WebSocket com o servidor para:
 * - Envio de localização em tempo real
 * - Recebimento de notificações instantâneas
 * - Comunicação bidirecional eficiente
 */

class SocketService {
  private socket: Socket | null = null;
  private isConnected: boolean = false;
  private userId: string | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  // Callbacks
  private onLocationUpdatedCallback?: (data: any) => void;
  private onOutbreakAlertCallback?: (data: any) => void;
  private onNotificationCallback?: (data: any) => void;
  private onConnectedCallback?: () => void;
  private onDisconnectedCallback?: () => void;

  /**
   * Inicializa e conecta ao servidor Socket.IO
   */
  async connect(): Promise<boolean> {
    try {
      if (this.isConnected && this.socket) {
        console.log('Socket.IO já está conectado');
        return true;
      }

      this.userId = await getDeviceId();

      // Criar conexão Socket.IO
      this.socket = io(API_BASE_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: 1000,
        timeout: 10000,
      });

      // Setup event listeners
      this.setupEventListeners();

      return new Promise((resolve) => {
        this.socket?.on('connect', () => {
          console.log('✅ Socket.IO conectado:', this.socket?.id);
          this.isConnected = true;
          this.reconnectAttempts = 0;

          // Autenticar usuário
          this.authenticate();

          resolve(true);
        });

        this.socket?.on('connect_error', (error) => {
          console.error('❌ Erro de conexão Socket.IO:', error.message);
          this.reconnectAttempts++;

          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            resolve(false);
          }
        });
      });
    } catch (error) {
      console.error('❌ Erro ao conectar Socket.IO:', error);
      return false;
    }
  }

  /**
   * Autentica o usuário com o servidor
   */
  private authenticate() {
    if (!this.socket || !this.userId) return;

    this.socket.emit('authenticate', {
      user_id: this.userId,
    });

    console.log('🔐 Autenticando usuário:', this.userId);
  }

  /**
   * Configura listeners de eventos
   */
  private setupEventListeners() {
    if (!this.socket) return;

    // Evento de conexão
    this.socket.on('connect', () => {
      console.log('🔌 Socket.IO conectado');
      this.isConnected = true;
      this.onConnectedCallback?.();
    });

    // Evento de desconexão
    this.socket.on('disconnect', (reason) => {
      console.log('🔌 Socket.IO desconectado:', reason);
      this.isConnected = false;
      this.onDisconnectedCallback?.();
    });

    // Autenticação confirmada
    this.socket.on('authenticated', (data) => {
      console.log('✅ Autenticado:', data);
    });

    // Localização atualizada
    this.socket.on('location_updated', (data) => {
      console.log('📍 Localização atualizada:', data);
      this.onLocationUpdatedCallback?.(data);
    });

    // Alerta de surto
    this.socket.on('outbreak_alert', (data) => {
      console.log('🚨 ALERTA DE SURTO recebido:', data);
      this.onOutbreakAlertCallback?.(data);
    });

    // Notificação genérica
    this.socket.on('notification', (data) => {
      console.log('📢 Notificação recebida:', data);
      this.onNotificationCallback?.(data);
    });

    // Usuários próximos
    this.socket.on('nearby_users', (data) => {
      console.log('👥 Usuários próximos:', data.count);
    });

    // Pong (resposta ao ping)
    this.socket.on('pong', (data) => {
      console.log('🏓 Pong recebido:', data.timestamp);
    });

    // Erro
    this.socket.on('error', (data) => {
      console.error('❌ Erro do servidor:', data.message);
    });
  }

  /**
   * Envia atualização de localização em tempo real
   */
  sendLocationUpdate(latitude: number, longitude: number, timestamp?: string): void {
    if (!this.socket || !this.isConnected) {
      console.warn('⚠️ Socket.IO não conectado. Localização não enviada.');
      return;
    }

    this.socket.emit('update_location', {
      latitude,
      longitude,
      timestamp: timestamp || new Date().toISOString(),
    });

    console.log('📍 Localização enviada via Socket.IO:', {
      lat: latitude.toFixed(6),
      lng: longitude.toFixed(6),
    });
  }

  /**
   * Busca usuários próximos
   */
  getNearbyUsers(latitude: number, longitude: number, radiusKm: number = 5.0): void {
    if (!this.socket || !this.isConnected) {
      console.warn('⚠️ Socket.IO não conectado.');
      return;
    }

    this.socket.emit('get_nearby_users', {
      latitude,
      longitude,
      radius_km: radiusKm,
    });
  }

  /**
   * Envia ping para manter conexão viva
   */
  sendPing(): void {
    if (!this.socket || !this.isConnected) return;

    this.socket.emit('ping', {
      timestamp: Date.now(),
    });
  }

  /**
   * Desconecta do servidor
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.isConnected = false;
      console.log('👋 Socket.IO desconectado');
    }
  }

  /**
   * Verifica se está conectado
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  /**
   * Retorna o ID do socket
   */
  getSocketId(): string | undefined {
    return this.socket?.id;
  }

  // ========== Callbacks ==========

  /**
   * Registra callback para quando localização for atualizada
   */
  onLocationUpdated(callback: (data: any) => void): void {
    this.onLocationUpdatedCallback = callback;
  }

  /**
   * Registra callback para alerta de surto
   */
  onOutbreakAlert(callback: (data: any) => void): void {
    this.onOutbreakAlertCallback = callback;
  }

  /**
   * Registra callback para notificações gerais
   */
  onNotification(callback: (data: any) => void): void {
    this.onNotificationCallback = callback;
  }

  /**
   * Registra callback para quando conectar
   */
  onConnected(callback: () => void): void {
    this.onConnectedCallback = callback;
  }

  /**
   * Registra callback para quando desconectar
   */
  onDisconnected(callback: () => void): void {
    this.onDisconnectedCallback = callback;
  }
}

// Instância global do serviço
export const socketService = new SocketService();
