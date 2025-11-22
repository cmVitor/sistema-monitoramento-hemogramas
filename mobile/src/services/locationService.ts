import * as Location from 'expo-location';
import { apiService } from './api';
import { getDeviceId } from '../utils/device';
import { LOCATION_UPDATE_INTERVAL } from '../config';

// Estado global para controlar o polling de localização
let locationPollingInterval: NodeJS.Timeout | null = null;
let isMonitoring = false;

export const locationService = {
  // Solicitar permissões de localização (apenas foreground para Expo Go)
  requestPermissions: async (): Promise<boolean> => {
    const { status: foregroundStatus } = await Location.requestForegroundPermissionsAsync();
    return foregroundStatus === 'granted';
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

    // Função para enviar localização e verificar surtos
    const sendLocation = async () => {
      try {
        const location = await locationService.getCurrentLocation();
        const deviceId = await getDeviceId();

        console.log('📍 Enviando localização:', {
          lat: location.coords.latitude.toFixed(6),
          lng: location.coords.longitude.toFixed(6),
        });

        const response = await apiService.sendLocationUpdate({
          device_id: deviceId,
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          timestamp: new Date(location.timestamp).toISOString(),
        });

        console.log('✅ Resposta da API:', {
          status: response.status,
          in_outbreak_zone: response.in_outbreak_zone,
          alert_sent: response.alert_sent
        });

        // Notificar IMEDIATAMENTE se está em zona de surto
        if (response.in_outbreak_zone && onLocationUpdate) {
          console.log('🚨 ALERTA: Você está em zona de surto!');
          onLocationUpdate(true);
        }
      } catch (error) {
        console.error('❌ Erro ao enviar localização:', error);
      }
    };

    // VERIFICAÇÃO IMEDIATA ao iniciar monitoramento
    console.log('🚀 Iniciando monitoramento - Verificação imediata...');
    await sendLocation();

    // Configurar polling rápido (5 segundos)
    console.log(`⏱️  Polling configurado: verificar a cada ${LOCATION_UPDATE_INTERVAL / 1000}s`);
    locationPollingInterval = setInterval(sendLocation, LOCATION_UPDATE_INTERVAL);
  },

  // Parar monitoramento
  stopForegroundLocationPolling: () => {
    if (locationPollingInterval) {
      clearInterval(locationPollingInterval);
      locationPollingInterval = null;
    }
    isMonitoring = false;
  },

  // Verificar se está rodando
  isLocationMonitoringActive: (): boolean => {
    return isMonitoring;
  },
};
