import React, { useEffect, useState, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  Alert,
  AppState,
} from 'react-native';
import { locationService } from './src/services/locationService';
import { notificationService } from './src/services/notificationService';
import { networkService } from './src/services/networkService';
import MapView from './src/components/MapView';
import * as Notifications from 'expo-notifications';

export default function App() {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [inOutbreakZone, setInOutbreakZone] = useState(false);
  const [alertCount, setAlertCount] = useState(0);
  const [isOnline, setIsOnline] = useState(true);

  // Refs para controlar cooldown de alertas
  const lastAlertTime = useRef<Date | null>(null);
  const previousOutbreakState = useRef<boolean>(false);
  const ALERT_COOLDOWN_MS = 5 * 60 * 1000; // 5 minutos entre alertas

  useEffect(() => {
    setupNotificationListeners();
    setupNetworkMonitoring();

    // Iniciar monitoramento automaticamente
    initializeAutoMonitoring();

    // Gerenciar estados do app (foreground/background)
    const subscription = AppState.addEventListener('change', nextAppState => {
      if (nextAppState === 'active') {
        console.log('📱 App voltou para foreground - Retomando monitoramento...');
        if (!isMonitoring && isOnline) {
          startMonitoringInternal();
        }
      } else if (nextAppState === 'background') {
        console.log('📱 App em background - Monitoramento continua (limitado pelo Expo Go)');
      }
    });

    return () => {
      subscription.remove();
      locationService.stopForegroundLocationPolling();
      locationService.stopBackgroundLocationTracking();
    };
  }, []);

  // Effect para gerenciar monitoramento baseado na conectividade
  useEffect(() => {
    if (isOnline && !isMonitoring) {
      console.log('📡 Online detectado - Iniciando monitoramento...');
      startMonitoringInternal();
    } else if (!isOnline && isMonitoring) {
      console.log('📴 Offline detectado - Pausando monitoramento...');
      locationService.stopForegroundLocationPolling();
      locationService.stopBackgroundLocationTracking();
      setIsMonitoring(false);
    }
  }, [isOnline]);

  const initializeAutoMonitoring = async () => {
    console.log('🚀 Inicializando monitoramento automático...');

    // Verificar conectividade inicial
    const connected = await networkService.isConnected();
    setIsOnline(connected);

    // Iniciar monitoramento se estiver online
    if (connected) {
      await startMonitoringInternal();
    } else {
      console.log('📴 Offline - Aguardando conexão para iniciar monitoramento...');
    }
  };

  const setupNetworkMonitoring = () => {
    // Monitorar mudanças na conectividade
    const unsubscribe = networkService.subscribe((connected) => {
      console.log('📡 Status de rede alterado:', connected ? 'Online' : 'Offline');
      setIsOnline(connected);
    });

    return unsubscribe;
  };

  const setupNotificationListeners = () => {
    // Listener para notificações recebidas
    notificationService.addNotificationListener((notification) => {
      console.log('Notificação recebida:', notification);
    });

    // Listener para quando usuário clica na notificação
    notificationService.addNotificationResponseListener((response) => {
      console.log('Usuário interagiu com notificação:', response);
      Alert.alert(
        '⚠️ Alerta de Surto',
        'Você está próximo a uma região de surto. Evite aglomerações e procure orientação médica se necessário.'
      );
    });
  };

  // Função para iniciar monitoramento automaticamente
  const startMonitoringInternal = async () => {
    try {
      // Solicitar permissões de localização
      const hasPermissions = await locationService.requestPermissions();
      if (!hasPermissions) {
        console.log('❌ Permissões de localização não concedidas');
        Alert.alert(
          'Permissões Necessárias',
          'O aplicativo precisa de acesso à sua localização para alertá-lo sobre zonas de surto.',
          [{ text: 'OK' }]
        );
        return;
      }

      // Registrar dispositivo para notificações (silenciosamente)
      try {
        await notificationService.registerDevice();
        console.log('✅ Dispositivo registrado para notificações');
      } catch (error) {
        console.log('⚠️ Falha ao registrar dispositivo para notificações:', error);
      }

      // Obter localização atual
      const location = await locationService.getCurrentLocation();
      setCurrentLocation({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      });

      // Callback para atualizar localização e detectar zona de surto
      const onLocationUpdate = async (inZone: boolean) => {
        console.log('📍 Localização atualizada - Em zona de surto:', inZone);

        // Atualizar localização atual
        const location = await locationService.getCurrentLocation();
        setCurrentLocation({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
        });
        setLastUpdateTime(new Date());

        // Atualizar estado visual
        setInOutbreakZone(inZone);

        // DETECTAR MUDANÇA DE ESTADO: apenas alertar quando ENTRA na zona (transição false -> true)
        const stateChanged = inZone && !previousOutbreakState.current;

        if (stateChanged) {
          // Verificar cooldown para evitar flood de alertas
          const now = new Date();
          const timeSinceLastAlert = lastAlertTime.current
            ? now.getTime() - lastAlertTime.current.getTime()
            : Infinity;

          const canAlert = timeSinceLastAlert > ALERT_COOLDOWN_MS;

          if (canAlert) {
            console.log('🚨 NOVA ENTRADA EM ZONA DE SURTO - Enviando alerta');

            // Atualizar contador e timestamp
            setAlertCount(prev => prev + 1);
            lastAlertTime.current = now;

            // Enviar notificação (apenas uma vez)
            await notificationService.sendUrgentOutbreakAlert();

            // Mostrar alerta visual (apenas uma vez)
            Alert.alert(
              '🚨 ALERTA DE SURTO',
              'Você entrou em uma zona de surto ativo!\n\n' +
              '⚠️ Evite aglomerações\n' +
              '🏥 Procure atendimento se tiver sintomas\n' +
              '😷 Use máscara\n' +
              '🧼 Lave as mãos frequentemente',
              [{ text: 'ENTENDI', style: 'destructive' }]
            );
          } else {
            const minutesRemaining = Math.ceil((ALERT_COOLDOWN_MS - timeSinceLastAlert) / 60000);
            console.log(`⏳ Cooldown ativo - próximo alerta em ${minutesRemaining} minutos`);
          }
        } else if (!inZone && previousOutbreakState.current) {
          // Saiu da zona de surto
          console.log('✅ Você saiu da zona de surto');
        }

        // Atualizar estado anterior
        previousOutbreakState.current = inZone;
      };

      // Iniciar monitoramento em foreground
      console.log('🚀 Monitoramento automático iniciado');
      await locationService.startForegroundLocationPolling(onLocationUpdate);

      // Tentar iniciar monitoramento em background (silenciosamente, pois não funciona no Expo Go)
      try {
        await locationService.startBackgroundLocationTracking(onLocationUpdate);
        console.log('✅ Background tracking ativo (build standalone)');
      } catch (error) {
        // Silencioso: background não funciona no Expo Go, mas foreground funciona perfeitamente
      }

      setIsMonitoring(true);
      setLastUpdateTime(new Date());

      console.log('✅ Monitoramento ativo - Você será alertado se entrar em zona de surto');
    } catch (error: any) {
      console.error('❌ Erro ao iniciar monitoramento:', error);
    }
  };


  return (
    <View style={styles.container}>
      {/* Banner de Status no Topo */}
      <View style={styles.statusBar}>
        <View style={[styles.statusIndicator, !isOnline && styles.statusIndicatorOffline]}>
          <Text style={styles.statusText}>
            {isOnline ? '● Online' : '○ Offline'}
          </Text>
        </View>
        <View style={[styles.monitoringIndicator, isMonitoring && styles.monitoringIndicatorActive]}>
          <Text style={styles.monitoringText}>
            {isMonitoring ? '● Monitorando' : '○ Aguardando'}
          </Text>
        </View>
        {lastUpdateTime && (
          <Text style={styles.lastUpdateText}>
            {lastUpdateTime.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
          </Text>
        )}
      </View>

      {/* Mapa em Tela Cheia */}
      <MapView currentLocation={currentLocation} inOutbreakZone={inOutbreakZone} />

      {/* Banner de Alerta de Surto (sobreposto ao mapa) */}
      {inOutbreakZone && (
        <View style={styles.outbreakAlert}>
          <Text style={styles.outbreakAlertIcon}>🚨</Text>
          <View style={styles.outbreakAlertContent}>
            <Text style={styles.outbreakAlertTitle}>ZONA DE SURTO ATIVA</Text>
            <Text style={styles.outbreakAlertText}>
              Você está em uma região com surto detectado
            </Text>
            <Text style={styles.outbreakAlertCount}>
              Alertas recebidos: {alertCount}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  statusBar: {
    position: 'absolute',
    top: 50,
    left: 10,
    right: 10,
    zIndex: 1000,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 12,
    padding: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  statusIndicator: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    marginRight: 8,
  },
  statusIndicatorOffline: {
    backgroundColor: '#f44336',
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  monitoringIndicator: {
    backgroundColor: '#9E9E9E',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    marginRight: 8,
  },
  monitoringIndicatorActive: {
    backgroundColor: '#2196F3',
  },
  monitoringText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  lastUpdateText: {
    flex: 1,
    textAlign: 'right',
    fontSize: 11,
    color: '#666',
    fontWeight: '500',
  },
  outbreakAlert: {
    position: 'absolute',
    bottom: 100,
    left: 10,
    right: 10,
    zIndex: 1000,
    backgroundColor: 'rgba(220, 38, 38, 0.98)',
    borderRadius: 16,
    padding: 20,
    borderWidth: 3,
    borderColor: '#fbbf24',
    shadowColor: '#FF0000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.6,
    shadowRadius: 10,
    elevation: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },
  outbreakAlertIcon: {
    fontSize: 40,
    marginRight: 15,
  },
  outbreakAlertContent: {
    flex: 1,
  },
  outbreakAlertTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 6,
  },
  outbreakAlertText: {
    fontSize: 13,
    color: '#FFFFFF',
    marginBottom: 4,
  },
  outbreakAlertCount: {
    fontSize: 11,
    color: '#fbbf24',
    fontWeight: '600',
    marginTop: 4,
  },
});
