import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import { socketService } from './socketService';
import { notificationService } from './notificationService';
import { apiService } from './api';
import { getDeviceId } from '../utils/device';
import { LOCATION_UPDATE_INTERVAL } from '../config';

// ----------------------------------------------------------------------
// 1. Constantes e Estado Global do Serviço
// ----------------------------------------------------------------------

/** Nome da tarefa registrada no TaskManager do Expo para background. */
const BACKGROUND_LOCATION_TASK = 'realtime-location-task';

// Variáveis de controle de estado (Module-level state)
let isMonitoring = false;
let isInOutbreakZone = false;
let locationInterval: NodeJS.Timeout | null = null;
let pingInterval: NodeJS.Timeout | null = null;

// ----------------------------------------------------------------------
// 2. Definição da Tarefa de Background (Expo Task Manager)
// ----------------------------------------------------------------------

/**
 * Define a tarefa que será executada quando o app estiver em segundo plano
 * e receber uma atualização de geolocalização do sistema operacional.
 */
TaskManager.defineTask(BACKGROUND_LOCATION_TASK, async ({ data, error }) => {
  if (error) {
    console.error('❌ Erro na tarefa de background:', error);
    return;
  }

  if (data) {
    const { locations } = data as { locations: Location.LocationObject[] };
    const location = locations[0];

    // Se tivermos localização e conexão Socket ativa, enviamos imediatamente
    if (location && socketService.getConnectionStatus()) {
      socketService.sendLocationUpdate(
        location.coords.latitude,
        location.coords.longitude,
        new Date(location.timestamp).toISOString()
      );
    }
  }
});

// ----------------------------------------------------------------------
// 3. Serviço Realtime Principal
// ----------------------------------------------------------------------

export const realtimeService = {
  
  // --- Inicialização e Configuração ---

  /**
   * Inicializa o serviço completo: pede permissões, conecta ao Socket.IO
   * e configura os ouvintes de eventos (listeners).
   * @returns {Promise<boolean>} Sucesso da inicialização.
   */
  initialize: async (): Promise<boolean> => {
    try {
      console.log('🚀 Inicializando serviço realtime...');

      // 1. Solicitar permissões de Localização (Foreground)
      const hasLocationPermission = await Location.requestForegroundPermissionsAsync();
      if (hasLocationPermission.status !== 'granted') {
        console.error('❌ Permissão de localização negada');
        return false;
      }

      // 2. Solicitar permissões de Notificação
      const hasNotificationPermission = await notificationService.requestPermissions();
      if (!hasNotificationPermission) {
        console.warn('⚠️ Permissão de notificação negada');
      }

      // 3. Conectar ao Socket.IO
      const connected = await socketService.connect();
      if (!connected) {
        console.warn('⚠️ Falha ao conectar Socket.IO - usando fallback REST API');
      }

      // 4. Configurar Callbacks do Socket
      socketService.onOutbreakAlert((data) => {
        console.log('🚨 ALERTA DE SURTO recebido via Socket.IO:', data);
        isInOutbreakZone = true;
        notificationService.sendLocalOutbreakAlert(true);
      });

      socketService.onNotification((data) => {
        console.log('📢 Notificação recebida:', data);
        // Lógica futura para notificações genéricas
      });

      socketService.onConnected(() => {
        console.log('✅ Socket.IO conectado - modo realtime ativo');
      });

      socketService.onDisconnected(() => {
        console.log('⚠️ Socket.IO desconectado - ativando fallback');
      });

      // 5. Registrar dispositivo no backend (Firebase/BD)
      await notificationService.registerDevice();

      console.log('✅ Serviço realtime inicializado com sucesso');
      return true;

    } catch (error) {
      console.error('❌ Erro ao inicializar serviço realtime:', error);
      return false;
    }
  },

  /**
   * Encerra todas as conexões e para os monitoramentos.
   */
  disconnect: () => {
    realtimeService.stopLocationMonitoring();
    socketService.disconnect();
    console.log('👋 Serviço realtime desconectado');
  },

  // --- Monitoramento em Primeiro Plano (Foreground) ---

  /**
   * Inicia o loop de monitoramento de localização enquanto o app está aberto.
   * Gerencia a alternância automática entre Socket.IO e REST API (Fallback).
   * @param onOutbreakZoneChange Callback opcional disparado quando o status de zona de risco muda.
   */
  startLocationMonitoring: async (
    onOutbreakZoneChange?: (inZone: boolean) => void
  ): Promise<boolean> => {
    try {
      if (isMonitoring) {
        console.log('⚠️ Monitoramento já está ativo');
        return true;
      }

      console.log('📍 Iniciando monitoramento de localização...');

      // --- Passo A: Captura e Envio Inicial ---
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      if (socketService.getConnectionStatus()) {
        // Via Socket.IO (Tempo Real)
        socketService.sendLocationUpdate(
          location.coords.latitude,
          location.coords.longitude
        );
      } else {
        // Via REST API (Fallback)
        const deviceId = await getDeviceId();
        await apiService.sendLocationUpdate({
          device_id: deviceId,
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          timestamp: new Date(location.timestamp).toISOString(),
        });
      }

      // --- Passo B: Verificação Inicial de Zona de Surto ---
      const inZone = await apiService.checkOutbreakZone(
        location.coords.latitude,
        location.coords.longitude
      );

      isInOutbreakZone = inZone;
      onOutbreakZoneChange?.(inZone);

      if (inZone) {
        console.log('🚨 VOCÊ ESTÁ EM ZONA DE SURTO!');
        notificationService.sendLocalOutbreakAlert(true);
      }

      // --- Passo C: Configurar Loop de Monitoramento (Intervalo) ---
      locationInterval = setInterval(async () => {
        try {
          const currentLocation = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });

          // 1. Tentar enviar via Socket
          if (socketService.getConnectionStatus()) {
            socketService.sendLocationUpdate(
              currentLocation.coords.latitude,
              currentLocation.coords.longitude
            );
          } else {
            // 2. Fallback: Enviar via API e checar resposta
            const deviceId = await getDeviceId();
            const response = await apiService.sendLocationUpdate({
              device_id: deviceId,
              latitude: currentLocation.coords.latitude,
              longitude: currentLocation.coords.longitude,
              timestamp: new Date(currentLocation.timestamp).toISOString(),
            });

            // Atualizar status baseado na resposta da API de update
            if (response.in_outbreak_zone !== isInOutbreakZone) {
              isInOutbreakZone = response.in_outbreak_zone;
              onOutbreakZoneChange?.(response.in_outbreak_zone);

              if (response.in_outbreak_zone) {
                notificationService.sendUrgentOutbreakAlert();
              }
            }
          }

          // 3. Verificação explícita de zona (Double check para garantir consistência)
          const currentlyInZone = await apiService.checkOutbreakZone(
            currentLocation.coords.latitude,
            currentLocation.coords.longitude
          );

          if (currentlyInZone !== isInOutbreakZone) {
            isInOutbreakZone = currentlyInZone;
            onOutbreakZoneChange?.(currentlyInZone);

            if (currentlyInZone) {
              notificationService.sendUrgentOutbreakAlert();
            }
          }

        } catch (error) {
          console.error('❌ Erro ao atualizar localização no intervalo:', error);
        }
      }, LOCATION_UPDATE_INTERVAL);

      // --- Passo D: Configurar Ping (Keep-Alive) do Socket ---
      if (socketService.getConnectionStatus()) {
        pingInterval = setInterval(() => {
          socketService.sendPing();
        }, 30000); // 30 segundos
      }

      isMonitoring = true;
      console.log('✅ Monitoramento iniciado');
      console.log(`📍 Atualizando a cada ${LOCATION_UPDATE_INTERVAL / 60000} minutos`);

      return true;

    } catch (error) {
      console.error('❌ Erro ao iniciar monitoramento:', error);
      return false;
    }
  },

  /**
   * Para o loop de monitoramento (setIntervals) e limpa os timers.
   */
  stopLocationMonitoring: () => {
    if (locationInterval) {
      clearInterval(locationInterval);
      locationInterval = null;
    }

    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }

    isMonitoring = false;
    console.log('🛑 Monitoramento parado');
  },

  // --- Monitoramento em Segundo Plano (Background) ---

  /**
   * Registra e inicia o serviço de localização em background.
   * Nota: Isso requer permissões específicas no Android/iOS e não funciona no Expo Go.
   */
  startBackgroundTracking: async (): Promise<boolean> => {
    try {
      const { status } = await Location.requestBackgroundPermissionsAsync();
      if (status !== 'granted') {
        console.warn('⚠️ Permissão de background negada');
        return false;
      }

      await Location.startLocationUpdatesAsync(BACKGROUND_LOCATION_TASK, {
        accuracy: Location.Accuracy.Balanced,
        timeInterval: LOCATION_UPDATE_INTERVAL,
        distanceInterval: 50, // Apenas atualiza se mover 50 metros
        foregroundService: {
          notificationTitle: '📍 Monitoramento de Localização',
          notificationBody: 'Rastreando sua localização para alertas de surto',
          notificationColor: '#FF6B6B',
        },
      });

      console.log('✅ Background tracking iniciado');
      return true;

    } catch (error) {
      console.error('❌ Erro ao iniciar background tracking:', error);
      return false;
    }
  },

  /**
   * Para o serviço de localização em background.
   */
  stopBackgroundTracking: async () => {
    try {
      const isTaskDefined = await TaskManager.isTaskRegisteredAsync(BACKGROUND_LOCATION_TASK);
      if (isTaskDefined) {
        await Location.stopLocationUpdatesAsync(BACKGROUND_LOCATION_TASK);
        console.log('✅ Background tracking parado');
      }
    } catch (error) {
      console.error('❌ Erro ao parar background tracking:', error);
    }
  },

  // --- Utilitários e Getters ---

  /** Retorna se o monitoramento (foreground) está ativo. */
  isMonitoring: (): boolean => {
    return isMonitoring;
  },

  /** Retorna se o usuário está atualmente em uma zona de risco. */
  isInOutbreakZone: (): boolean => {
    return isInOutbreakZone;
  },

  /** Retorna o status da conexão Socket.IO. */
  getConnectionStatus: (): boolean => {
    return socketService.getConnectionStatus();
  },

  /**
   * Solicita via Socket a lista de usuários próximos (feature social/mapa).
   * @param radiusKm Raio de busca em quilômetros.
   */
  getNearbyUsers: async (radiusKm: number = 5.0) => {
    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      socketService.getNearbyUsers(
        location.coords.latitude,
        location.coords.longitude,
        radiusKm
      );
    } catch (error) {
      console.error('Erro ao buscar usuários próximos:', error);
    }
  },
};