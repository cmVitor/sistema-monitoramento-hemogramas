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
  sendLocalOutbreakAlert: async (force: boolean = false) => {
    try {
      console.log('📢 Enviando notificação local de alerta...');

      // Enviar notificação IMEDIATAMENTE com máxima prioridade
      await Notifications.scheduleNotificationAsync({
        content: {
          title: '🚨 ALERTA DE SURTO!',
          body: 'ATENÇÃO! Você está em uma zona de surto ativo. Evite aglomerações e procure atendimento médico se necessário.',
          sound: true,
          priority: Notifications.AndroidNotificationPriority.MAX,
          vibrate: [0, 250, 250, 250], // Vibrar 3 vezes
          data: {
            type: 'outbreak_alert',
            timestamp: Date.now(),
            force: force
          },
          badge: 1,
        },
        trigger: null, // Enviar IMEDIATAMENTE
      });

      console.log('✅ Notificação enviada com sucesso!');
    } catch (error) {
      console.error('❌ Erro ao enviar notificação local:', error);
    }
  },

  // Enviar múltiplas notificações para garantir que o usuário veja
  sendUrgentOutbreakAlert: async () => {
    try {
      console.log('🚨 Enviando alerta URGENTE de surto...');

      // Primeira notificação - Imediata
      await notificationService.sendLocalOutbreakAlert(true);

      // Segunda notificação após 2 segundos (backup)
      setTimeout(async () => {
        await Notifications.scheduleNotificationAsync({
          content: {
            title: '⚠️ Confirmação de Alerta',
            body: 'Você continua em zona de surto. Mantenha-se alerta!',
            sound: true,
            priority: Notifications.AndroidNotificationPriority.HIGH,
            data: { type: 'outbreak_confirmation' },
          },
          trigger: { seconds: 0 },
        });
      }, 2000);

      console.log('✅ Alertas urgentes enviados!');
    } catch (error) {
      console.error('❌ Erro ao enviar alertas urgentes:', error);
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
