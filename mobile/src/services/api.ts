import axios from 'axios';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface RegisterDeviceRequest {
  fcm_token: string;
  device_id: string;
  platform: 'ios' | 'android';
}

export interface LocationUpdate {
  device_id: string;
  latitude: number;
  longitude: number;
  timestamp: string;
}

export interface OutbreakRegion {
  centroid: {
    lat: number;
    lng: number;
  };
  radius: number;
  point_count: number;
}

export const apiService = {
  // Registrar dispositivo com token FCM
  registerDevice: async (data: RegisterDeviceRequest) => {
    return api.post('/api/mobile/register', data);
  },

  // Enviar atualização de localização
  sendLocationUpdate: async (data: LocationUpdate) => {
    return api.post('/api/mobile/location', data);
  },

  // Verificar regiões de surto (opcional - para exibir no mapa)
  getOutbreakRegions: async (): Promise<OutbreakRegion | null> => {
    const response = await api.get('/api/heatmap/outbreak-data');
    return response.data.outbreak || null;
  },
};

export default api;
