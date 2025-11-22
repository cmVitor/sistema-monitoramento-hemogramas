import React, { useEffect, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Alert,
  ScrollView,
  ActivityIndicator,
  AppState,
} from 'react-native';
import { locationService } from './src/services/locationService';
import { notificationService } from './src/services/notificationService';
import * as Notifications from 'expo-notifications';

export default function App() {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [isRegistered, setIsRegistered] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [inOutbreakZone, setInOutbreakZone] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    checkInitialState();
    setupNotificationListeners();

    // Parar monitoramento quando app vai para background
    const subscription = AppState.addEventListener('change', nextAppState => {
      if (nextAppState === 'background' && isMonitoring) {
        console.log('App em background - monitoramento pausado (limitação Expo Go)');
      }
    });

    return () => {
      subscription.remove();
      locationService.stopForegroundLocationPolling();
    };
  }, []);

  const checkInitialState = async () => {
    const isActive = locationService.isLocationMonitoringActive();
    setIsMonitoring(isActive);
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

  const handleRegisterDevice = async () => {
    setLoading(true);
    try {
      const success = await notificationService.registerDevice();
      if (success) {
        setIsRegistered(true);
        Alert.alert('Sucesso', 'Dispositivo registrado para monitoramento!');
      } else {
        Alert.alert('Aviso', 'Dispositivo registrado com limitações do Expo Go');
        setIsRegistered(true); // Continuar mesmo assim
      }
    } catch (error) {
      Alert.alert('Erro', 'Falha ao registrar dispositivo');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartMonitoring = async () => {
    setLoading(true);
    try {
      const hasPermissions = await locationService.requestPermissions();
      if (!hasPermissions) {
        Alert.alert(
          'Permissões Necessárias',
          'É necessário conceder permissão de localização para receber alertas de surto.'
        );
        setLoading(false);
        return;
      }

      if (!isRegistered) {
        await handleRegisterDevice();
      }

      // Callback IMEDIATO para quando detectar zona de surto
      const onOutbreakDetected = async (inZone: boolean) => {
        console.log('🚨 Callback de surto acionado! inZone:', inZone);

        if (inZone) {
          // Atualizar estado IMEDIATAMENTE
          setInOutbreakZone(true);
          setAlertCount(prev => prev + 1);

          // Enviar notificações URGENTES
          await notificationService.sendUrgentOutbreakAlert();

          // Mostrar alert IMEDIATO e proeminente
          Alert.alert(
            '🚨 ALERTA DE SURTO DETECTADO!',
            'ATENÇÃO! Você está em uma zona de surto ativo!\n\n' +
            '⚠️ Evite aglomerações\n' +
            '🏥 Procure atendimento médico se tiver sintomas\n' +
            '😷 Use máscara\n' +
            '🧼 Lave as mãos frequentemente',
            [
              {
                text: 'ENTENDI',
                style: 'destructive'
              }
            ],
            { cancelable: false }
          );
        } else {
          setInOutbreakZone(false);
        }
      };

      // Iniciar monitoramento com verificação IMEDIATA
      console.log('🚀 Iniciando monitoramento...');
      await locationService.startForegroundLocationPolling(onOutbreakDetected);

      setIsMonitoring(true);
      setLastUpdateTime(new Date());

      Alert.alert(
        'Monitoramento Ativo',
        'Verificação a cada 5 segundos. Você será alertado IMEDIATAMENTE se entrar em zona de surto.\n\nMantenha o app aberto para detecção contínua.'
      );
    } catch (error: any) {
      Alert.alert('Erro', error.message || 'Não foi possível iniciar o monitoramento');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleStopMonitoring = async () => {
    setLoading(true);
    try {
      locationService.stopForegroundLocationPolling();
      setIsMonitoring(false);
      Alert.alert('Monitoramento Pausado', 'Você não receberá mais alertas de surto');
    } catch (error) {
      Alert.alert('Erro', 'Não foi possível parar o monitoramento');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleGetCurrentLocation = async () => {
    setLoading(true);
    try {
      const location = await locationService.getCurrentLocation();
      setCurrentLocation({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      });
      setLastUpdateTime(new Date());
    } catch (error) {
      Alert.alert('Erro', 'Não foi possível obter localização');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Alerta de Surtos</Text>
        <Text style={styles.subtitle}>Monitoramento em Tempo Real</Text>
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
        {/* ALERTA DE SURTO - Banner Vermelho */}
        {inOutbreakZone && (
          <View style={styles.outbreakBanner}>
            <Text style={styles.outbreakIcon}>🚨</Text>
            <Text style={styles.outbreakTitle}>VOCÊ ESTÁ EM ZONA DE SURTO!</Text>
            <Text style={styles.outbreakText}>
              Evite aglomerações e procure orientação médica se necessário
            </Text>
            <Text style={styles.outbreakCount}>
              Alertas recebidos: {alertCount}
            </Text>
          </View>
        )}

        {/* Banner de aviso Expo Go */}
        {!inOutbreakZone && (
          <View style={styles.warningBanner}>
            <Text style={styles.warningText}>
              ℹ️ Verificação a cada 5 segundos • Alerta instantâneo
            </Text>
          </View>
        )}

        <View style={styles.statusCard}>
          <Text style={styles.statusLabel}>Status do Monitoramento</Text>
          <View style={[styles.statusBadge, isMonitoring && styles.statusBadgeActive]}>
            <Text style={[styles.statusText, isMonitoring && styles.statusTextActive]}>
              {isMonitoring ? '✓ Ativo' : '○ Inativo'}
            </Text>
          </View>
          {lastUpdateTime && isMonitoring && (
            <Text style={styles.lastUpdateText}>
              Última atualização: {lastUpdateTime.toLocaleTimeString('pt-BR')}
            </Text>
          )}
        </View>

        {currentLocation && (
          <View style={styles.locationCard}>
            <Text style={styles.cardTitle}>Localização Atual</Text>
            <Text style={styles.locationText}>Lat: {currentLocation.latitude.toFixed(6)}</Text>
            <Text style={styles.locationText}>Lng: {currentLocation.longitude.toFixed(6)}</Text>
          </View>
        )}

        <View style={styles.buttonsContainer}>
          {!isMonitoring ? (
            <TouchableOpacity
              style={[styles.button, styles.buttonPrimary, loading && styles.buttonDisabled]}
              onPress={handleStartMonitoring}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Iniciar Monitoramento</Text>
              )}
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.button, styles.buttonDanger, loading && styles.buttonDisabled]}
              onPress={handleStopMonitoring}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Parar Monitoramento</Text>
              )}
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={[styles.button, styles.buttonSecondary, loading && styles.buttonDisabled]}
            onPress={handleGetCurrentLocation}
            disabled={loading}
          >
            <Text style={styles.buttonTextSecondary}>Ver Minha Localização</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#FF6B6B',
    paddingTop: 60,
    paddingBottom: 30,
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#fff',
    opacity: 0.9,
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 20,
  },
  outbreakBanner: {
    backgroundColor: '#FF0000',
    borderRadius: 12,
    padding: 20,
    marginBottom: 15,
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#8B0000',
    shadowColor: '#FF0000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 8,
  },
  outbreakIcon: {
    fontSize: 48,
    marginBottom: 10,
  },
  outbreakTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 10,
    textAlign: 'center',
  },
  outbreakText: {
    fontSize: 14,
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 8,
  },
  outbreakCount: {
    fontSize: 12,
    color: '#FFE0E0',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  warningBanner: {
    backgroundColor: '#FFF3CD',
    borderRadius: 8,
    padding: 12,
    marginBottom: 15,
    borderLeftWidth: 4,
    borderLeftColor: '#FFC107',
  },
  warningText: {
    fontSize: 13,
    color: '#856404',
    textAlign: 'center',
  },
  statusCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusLabel: {
    fontSize: 16,
    color: '#666',
    marginBottom: 10,
  },
  statusBadge: {
    backgroundColor: '#f0f0f0',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  statusBadgeActive: {
    backgroundColor: '#4CAF50',
  },
  statusText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  statusTextActive: {
    color: '#fff',
  },
  lastUpdateText: {
    fontSize: 12,
    color: '#999',
    marginTop: 10,
    fontStyle: 'italic',
  },
  locationCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  locationText: {
    fontSize: 14,
    color: '#666',
    fontFamily: 'monospace',
    marginVertical: 2,
  },
  infoCard: {
    backgroundColor: '#E3F2FD',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1976D2',
    marginBottom: 10,
  },
  infoText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 22,
  },
  buttonsContainer: {
    gap: 12,
  },
  button: {
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonPrimary: {
    backgroundColor: '#4CAF50',
  },
  buttonDanger: {
    backgroundColor: '#f44336',
  },
  buttonSecondary: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#FF6B6B',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonTextSecondary: {
    color: '#FF6B6B',
    fontSize: 16,
    fontWeight: '600',
  },
});
