import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { apiService } from './api';
import { getDeviceId } from '../utils/device';

// Configurar como as notificações devem ser tratadas quando recebidas
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export const notificationService = {
  // Solicitar permissões de notificação
  requestPermissions: async (): Promise<boolean> => {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    return finalStatus === 'granted';
  },

  // Registrar dispositivo no backend (versão simplificada para Expo Go)
  // NOTA: Push notifications remotas não funcionam no Expo Go SDK 53+
  // Este método registra o dispositivo apenas para tracking
  registerDevice: async (): Promise<boolean> => {
    try {
      const hasPermission = await notificationService.requestPermissions();
      if (!hasPermission) {
        console.warn('Permissão de notificação negada');
      }

      const deviceId = await getDeviceId();

      // Registrar sem token push (será usado apenas para location tracking)
      await apiService.registerDevice({
        fcm_token: `expo-go-${deviceId}`, // Token fictício para Expo Go
        device_id: deviceId,
        platform: Platform.OS as 'ios' | 'android',
      });

      console.log('Dispositivo registrado para tracking (Expo Go mode)');
      return true;
    } catch (error) {
      console.error('Erro ao registrar dispositivo:', error);
      return false;
    }
  },

  // Enviar notificação local quando entrar em zona de surto
  sendLocalOutbreakAlert: async () => {
    try {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: '⚠️ Alerta de Surto!',
          body: 'Você está próximo a uma região com surto detectado. Tome cuidado!',
          sound: true,
          priority: Notifications.AndroidNotificationPriority.HIGH,
          data: { type: 'outbreak_alert' },
        },
        trigger: null, // Enviar imediatamente
      });
    } catch (error) {
      console.error('Erro ao enviar notificação local:', error);
    }
  },

  // Adicionar listener para notificações recebidas
  addNotificationListener: (callback: (notification: Notifications.Notification) => void) => {
    return Notifications.addNotificationReceivedListener(callback);
  },

  // Adicionar listener para quando usuário interage com notificação
  addNotificationResponseListener: (
    callback: (response: Notifications.NotificationResponse) => void
  ) => {
    return Notifications.addNotificationResponseReceivedListener(callback);
  },
};
