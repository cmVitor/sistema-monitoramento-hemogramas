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
    const response = await api.post('/api/mobile/register', data);
    return response.data;
  },

  // Enviar atualização de localização
  sendLocationUpdate: async (data: LocationUpdate) => {
    const response = await api.post('/api/mobile/location', data);
    return response.data;
  },

  // Verificar regiões de surto (opcional - para exibir no mapa)
  getOutbreakRegions: async (): Promise<OutbreakRegion | null> => {
    const response = await api.get('/heatmap-data');
    const data = response.data;

    // O backend retorna { observations: [...], outbreaks: {...} }
    if (data.outbreaks && data.outbreaks.centroid) {
      return {
        centroid: {
          lat: data.outbreaks.centroid[0],
          lng: data.outbreaks.centroid[1],
        },
        radius: data.outbreaks.radius,
        point_count: data.outbreaks.point_count,
      };
    }

    return null;
  },

  // Verificar se localização está em zona de surto (endpoint leve, não atualiza BD)
  checkOutbreakZone: async (latitude: number, longitude: number): Promise<boolean> => {
    try {
      const response = await api.get('/api/mobile/check-outbreak-zone', {
        params: { latitude, longitude }
      });
      return response.data.in_outbreak_zone;
    } catch (error) {
      console.error('Erro ao verificar zona de surto:', error);
      return false;
    }
  },
};

export default api;
