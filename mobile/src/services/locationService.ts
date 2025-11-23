import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import { apiService } from './api';
import { getDeviceId } from '../utils/device';
import { LOCATION_UPDATE_INTERVAL, OUTBREAK_CHECK_INTERVAL, LOCATION_MIN_DISTANCE } from '../config';

// Nome da tarefa de background
const BACKGROUND_LOCATION_TASK = 'background-location-task';

// Estado global para controlar o polling de localização
let locationPollingInterval: NodeJS.Timeout | null = null;
let outbreakCheckInterval: NodeJS.Timeout | null = null;
let isMonitoring = false;
let backgroundCallback: ((inOutbreakZone: boolean) => void) | null = null;

// Definir tarefa de background para localização
TaskManager.defineTask(BACKGROUND_LOCATION_TASK, async ({ data, error }) => {
  if (error) {
    console.error('❌ Erro na tarefa de background:', error);
    return;
  }
  if (data) {
    const { locations } = data as { locations: Location.LocationObject[] };
    const location = locations[0];

    if (location) {
      try {
        const deviceId = await getDeviceId();

        console.log('📍 [Background] Enviando localização:', {
          lat: location.coords.latitude.toFixed(6),
          lng: location.coords.longitude.toFixed(6),
        });

        const response = await apiService.sendLocationUpdate({
          device_id: deviceId,
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          timestamp: new Date(location.timestamp).toISOString(),
        });

        console.log('✅ [Background] Resposta da API:', {
          status: response.status,
          in_outbreak_zone: response.in_outbreak_zone,
        });

        // Notificar se está em zona de surto
        if (response.in_outbreak_zone && backgroundCallback) {
          backgroundCallback(true);
        }
      } catch (error) {
        console.error('❌ [Background] Erro ao enviar localização:', error);
      }
    }
  }
});

export const locationService = {
  // Solicitar permissões de localização (foreground e background)
  requestPermissions: async (): Promise<boolean> => {
    // Primeiro solicitar permissão de foreground
    const { status: foregroundStatus } = await Location.requestForegroundPermissionsAsync();

    if (foregroundStatus !== 'granted') {
      return false;
    }

    // Tentar solicitar permissão de background (pode não funcionar no Expo Go)
    try {
      const { status: backgroundStatus } = await Location.requestBackgroundPermissionsAsync();
      console.log('📍 Permissão de background:', backgroundStatus);
    } catch (error) {
      console.log('⚠️ Background permission não disponível no Expo Go');
    }

    return true;
  },

  // Verificar se tem permissões
  hasPermissions: async (): Promise<boolean> => {
    const { status: foregroundStatus } = await Location.getForegroundPermissionsAsync();
    return foregroundStatus === 'granted';
  },

  // Obter localização atual
  getCurrentLocation: async () => {
    return await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
  },

  // Iniciar monitoramento em foreground (polling)
  // NOTA: No Expo Go, apenas foreground location funciona
  startForegroundLocationPolling: async (onLocationUpdate?: (inOutbreakZone: boolean) => void) => {
    const hasPermissions = await locationService.hasPermissions();
    if (!hasPermissions) {
      throw new Error('Permissões de localização não concedidas');
    }

    if (isMonitoring) {
      console.log('Monitoramento já está ativo');
      return;
    }

    isMonitoring = true;

    // Função para enviar localização completa ao servidor (atualiza BD)
    const sendLocation = async () => {
      try {
        const location = await locationService.getCurrentLocation();
        const deviceId = await getDeviceId();

        console.log('📍 [ENVIO COMPLETO] Enviando localização ao servidor:', {
          lat: location.coords.latitude.toFixed(6),
          lng: location.coords.longitude.toFixed(6),
        });

        const response = await apiService.sendLocationUpdate({
          device_id: deviceId,
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          timestamp: new Date(location.timestamp).toISOString(),
        });

        console.log('✅ Localização enviada:', {
          status: response.status,
          in_outbreak_zone: response.in_outbreak_zone,
          alert_sent: response.alert_sent
        });

        // Notificar se está em zona de surto
        if (response.in_outbreak_zone && onLocationUpdate) {
          onLocationUpdate(true);
        } else if (!response.in_outbreak_zone && onLocationUpdate) {
          onLocationUpdate(false);
        }
      } catch (error) {
        console.error('❌ Erro ao enviar localização:', error);
      }
    };

    // Função leve para verificar zona de surto (não atualiza BD)
    const checkOutbreakZone = async () => {
      try {
        const location = await locationService.getCurrentLocation();

        console.log('🔍 [VERIFICAÇÃO] Checando zona de surto:', {
          lat: location.coords.latitude.toFixed(6),
          lng: location.coords.longitude.toFixed(6),
        });

        const inOutbreakZone = await apiService.checkOutbreakZone(
          location.coords.latitude,
          location.coords.longitude
        );

        console.log(`${inOutbreakZone ? '🚨 EM ZONA DE SURTO!' : '✅ Fora de zona de surto'}`);

        // Notificar IMEDIATAMENTE se está em zona de surto
        if (onLocationUpdate) {
          onLocationUpdate(inOutbreakZone);
        }
      } catch (error) {
        console.error('❌ Erro ao verificar zona de surto:', error);
      }
    };

    // VERIFICAÇÃO IMEDIATA ao iniciar monitoramento
    console.log('🚀 Iniciando monitoramento - Verificação imediata...');
    await checkOutbreakZone();

    // Configurar polling de ENVIO DE LOCALIZAÇÃO (10 minutos)
    console.log(`📍 Envio de localização: a cada ${LOCATION_UPDATE_INTERVAL / 60000} minutos`);
    locationPollingInterval = setInterval(sendLocation, LOCATION_UPDATE_INTERVAL);

    // Configurar polling de VERIFICAÇÃO DE SURTO (30 segundos)
    console.log(`🔍 Verificação de surto: a cada ${OUTBREAK_CHECK_INTERVAL / 1000} segundos`);
    outbreakCheckInterval = setInterval(checkOutbreakZone, OUTBREAK_CHECK_INTERVAL);
  },

  // Parar monitoramento
  stopForegroundLocationPolling: () => {
    if (locationPollingInterval) {
      clearInterval(locationPollingInterval);
      locationPollingInterval = null;
    }
    if (outbreakCheckInterval) {
      clearInterval(outbreakCheckInterval);
      outbreakCheckInterval = null;
    }
    isMonitoring = false;
    console.log('🛑 Monitoramento parado');
  },

  // Iniciar monitoramento em background
  startBackgroundLocationTracking: async (onLocationUpdate?: (inOutbreakZone: boolean) => void) => {
    try {
      // Verificar se a tarefa já está registrada
      const isTaskDefined = await TaskManager.isTaskRegisteredAsync(BACKGROUND_LOCATION_TASK);
      if (isTaskDefined) {
        return;
      }

      // Salvar callback
      if (onLocationUpdate) {
        backgroundCallback = onLocationUpdate;
      }

      // Iniciar tracking de background
      await Location.startLocationUpdatesAsync(BACKGROUND_LOCATION_TASK, {
        accuracy: Location.Accuracy.Balanced,
        timeInterval: LOCATION_UPDATE_INTERVAL,
        distanceInterval: LOCATION_MIN_DISTANCE,
        foregroundService: {
          notificationTitle: 'Alerta de Surtos',
          notificationBody: 'Monitorando sua localização para alertas de surto',
          notificationColor: '#FF6B6B',
        },
      });

      console.log('✅ Background location tracking iniciado');
    } catch (error) {
      // Silencioso - esperado falhar no Expo Go
      throw error;
    }
  },

  // Parar monitoramento em background
  stopBackgroundLocationTracking: async () => {
    try {
      const isTaskDefined = await TaskManager.isTaskRegisteredAsync(BACKGROUND_LOCATION_TASK);
      if (isTaskDefined) {
        await Location.stopLocationUpdatesAsync(BACKGROUND_LOCATION_TASK);
        console.log('✅ Background location tracking parado');
      }
      backgroundCallback = null;
    } catch (error) {
      console.error('❌ Erro ao parar background tracking:', error);
    }
  },

  // Verificar se está rodando
  isLocationMonitoringActive: (): boolean => {
    return isMonitoring;
  },

  // Verificar se background tracking está ativo
  isBackgroundTrackingActive: async (): Promise<boolean> => {
    return await TaskManager.isTaskRegisteredAsync(BACKGROUND_LOCATION_TASK);
  },
};
