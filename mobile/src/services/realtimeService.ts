import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import { socketService } from './socketService';
import { notificationService } from './notificationService';
import { apiService } from './api';
import { getDeviceId } from '../utils/device';
import { LOCATION_UPDATE_INTERVAL, OUTBREAK_CHECK_INTERVAL } from '../config';

/**
 * Serviço Realtime - Integra Socket.IO + Location Tracking + Notifications
 *
 * Este serviço oferece comunicação em tempo real escalável para:
 * - Atualização de localização via Socket.IO (baixa latência)
 * - Notificações instantâneas de alertas de surto
 * - Fallback para API REST quando Socket.IO não disponível
 */

// Nome da tarefa de background
const BACKGROUND_LOCATION_TASK = 'realtime-location-task';

// Estado do serviço
let isMonitoring = false;
let locationInterval: NodeJS.Timeout | null = null;
let pingInterval: NodeJS.Timeout | null = null;
let isInOutbreakZone = false;

// Definir tarefa de background
TaskManager.defineTask(BACKGROUND_LOCATION_TASK, async ({ data, error }) => {
  if (error) {
    console.error('❌ Erro na tarefa de background:', error);
    return;
  }

  if (data) {
    const { locations } = data as { locations: Location.LocationObject[] };
    const location = locations[0];

    if (location && socketService.getConnectionStatus()) {
      // Enviar via Socket.IO (tempo real)
      socketService.sendLocationUpdate(
        location.coords.latitude,
        location.coords.longitude,
        new Date(location.timestamp).toISOString()
      );
    }
  }
});

export const realtimeService = {
  /**
   * Inicializa o serviço em tempo real
   */
  initialize: async (): Promise<boolean> => {
    try {
      console.log('🚀 Inicializando serviço realtime...');

      // 1. Solicitar permissões
      const hasLocationPermission = await Location.requestForegroundPermissionsAsync();
      if (hasLocationPermission.status !== 'granted') {
        console.error('❌ Permissão de localização negada');
        return false;
      }

      const hasNotificationPermission = await notificationService.requestPermissions();
      if (!hasNotificationPermission) {
        console.warn('⚠️ Permissão de notificação negada');
      }

      // 2. Conectar ao Socket.IO
      const connected = await socketService.connect();
      if (!connected) {
        console.warn('⚠️ Falha ao conectar Socket.IO - usando fallback REST API');
      }

      // 3. Registrar callbacks
      socketService.onOutbreakAlert((data) => {
        console.log('🚨 ALERTA DE SURTO recebido via Socket.IO:', data);
        isInOutbreakZone = true;
        notificationService.sendLocalOutbreakAlert(true);
      });

      socketService.onNotification((data) => {
        console.log('📢 Notificação recebida:', data);
        // Tratar outras notificações
      });

      socketService.onConnected(() => {
        console.log('✅ Socket.IO conectado - modo realtime ativo');
      });

      socketService.onDisconnected(() => {
        console.log('⚠️ Socket.IO desconectado - usando fallback');
      });

      // 4. Registrar dispositivo
      await notificationService.registerDevice();

      console.log('✅ Serviço realtime inicializado com sucesso');
      return true;

    } catch (error) {
      console.error('❌ Erro ao inicializar serviço realtime:', error);
      return false;
    }
  },

  /**
   * Inicia monitoramento de localização com Socket.IO
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

      // Verificação imediata
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      // Enviar localização inicial
      if (socketService.getConnectionStatus()) {
        // Via Socket.IO (tempo real)
        socketService.sendLocationUpdate(
          location.coords.latitude,
          location.coords.longitude
        );
      } else {
        // Fallback para REST API
        const deviceId = await getDeviceId();
        await apiService.sendLocationUpdate({
          device_id: deviceId,
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          timestamp: new Date(location.timestamp).toISOString(),
        });
      }

      // Verificar zona de surto inicial
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

      // Configurar polling de localização
      locationInterval = setInterval(async () => {
        try {
          const currentLocation = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });

          // Enviar via Socket.IO se conectado
          if (socketService.getConnectionStatus()) {
            socketService.sendLocationUpdate(
              currentLocation.coords.latitude,
              currentLocation.coords.longitude
            );
          } else {
            // Fallback para REST API
            const deviceId = await getDeviceId();
            const response = await apiService.sendLocationUpdate({
              device_id: deviceId,
              latitude: currentLocation.coords.latitude,
              longitude: currentLocation.coords.longitude,
              timestamp: new Date(currentLocation.timestamp).toISOString(),
            });

            // Atualizar status de zona de surto
            if (response.in_outbreak_zone !== isInOutbreakZone) {
              isInOutbreakZone = response.in_outbreak_zone;
              onOutbreakZoneChange?.(response.in_outbreak_zone);

              if (response.in_outbreak_zone) {
                notificationService.sendUrgentOutbreakAlert();
              }
            }
          }

          // Verificar zona de surto periodicamente
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
          console.error('❌ Erro ao atualizar localização:', error);
        }
      }, LOCATION_UPDATE_INTERVAL);

      // Configurar ping para manter conexão Socket.IO viva
      if (socketService.getConnectionStatus()) {
        pingInterval = setInterval(() => {
          socketService.sendPing();
        }, 30000); // Ping a cada 30 segundos
      }

      isMonitoring = true;
      console.log('✅ Monitoramento iniciado');
      console.log(`📍 Atualizando localização a cada ${LOCATION_UPDATE_INTERVAL / 60000} minutos`);

      return true;

    } catch (error) {
      console.error('❌ Erro ao iniciar monitoramento:', error);
      return false;
    }
  },

  /**
   * Para monitoramento de localização
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

  /**
   * Inicia tracking em background (não funciona no Expo Go)
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
        distanceInterval: 50,
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
   * Para tracking em background
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

  /**
   * Desconecta do serviço realtime
   */
  disconnect: () => {
    realtimeService.stopLocationMonitoring();
    socketService.disconnect();
    console.log('👋 Serviço realtime desconectado');
  },

  /**
   * Verifica se está monitorando
   */
  isMonitoring: (): boolean => {
    return isMonitoring;
  },

  /**
   * Verifica se está em zona de surto
   */
  isInOutbreakZone: (): boolean => {
    return isInOutbreakZone;
  },

  /**
   * Retorna status da conexão Socket.IO
   */
  getConnectionStatus: (): boolean => {
    return socketService.getConnectionStatus();
  },

  /**
   * Busca usuários próximos
   */
  getNearbyUsers: async (radiusKm: number = 5.0) => {
    const location = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });

    socketService.getNearbyUsers(
      location.coords.latitude,
      location.coords.longitude,
      radiusKm
    );
  },
};
