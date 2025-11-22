import * as Device from 'expo-device';
import AsyncStorage from '@react-native-async-storage/async-storage';

const DEVICE_ID_KEY = '@device_id';

export const getDeviceId = async (): Promise<string> => {
  // Tentar obter ID salvo
  let deviceId = await AsyncStorage.getItem(DEVICE_ID_KEY);

  if (!deviceId) {
    // Gerar novo ID baseado em informações do dispositivo
    const deviceInfo = [
      Device.modelName,
      Device.osName,
      Device.osVersion,
      Date.now().toString(),
    ].join('-');

    deviceId = `device-${btoa(deviceInfo).replace(/[^a-zA-Z0-9]/g, '')}`;
    await AsyncStorage.setItem(DEVICE_ID_KEY, deviceId);
  }

  return deviceId;
};
