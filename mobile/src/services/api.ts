import axios from 'axios';
import { API_BASE_URL } from '../config';

// ----------------------------------------------------------------------
// 1. Interfaces e Tipos
// (Definições movidas para o topo para facilitar a leitura dos contratos de dados)
// ----------------------------------------------------------------------

/** Estrutura para registro inicial do dispositivo e token FCM. */
export interface RegisterDeviceRequest {
  fcm_token: string;
  device_id: string;
  platform: 'ios' | 'android';
}

/** Estrutura do payload para atualização de telemetria. */
export interface LocationUpdate {
  device_id: string;
  latitude: number;
  longitude: number;
  timestamp: string;
}

/** Estrutura normalizada de uma região de surto para uso no mapa. */
export interface OutbreakRegion {
  centroid: {
    lat: number;
    lng: number;
  };
  radius: number;
  point_count: number;
}

// ----------------------------------------------------------------------
// 2. Configuração da Instância Axios
// ----------------------------------------------------------------------

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ----------------------------------------------------------------------
// 3. Serviço da API
// ----------------------------------------------------------------------

export const apiService = {
  /**
   * Registra um dispositivo móvel no backend associando-o a um token FCM.
   * @param data Objeto contendo token, ID do dispositivo e plataforma.
   */
  registerDevice: async (data: RegisterDeviceRequest) => {
    const response = await api.post('/api/mobile/register', data);
    return response.data;
  },

  /**
   * Envia os dados de geolocalização do usuário para o servidor.
   * @param data Objeto contendo coordenadas e timestamp.
   */
  sendLocationUpdate: async (data: LocationUpdate) => {
    const response = await api.post('/api/mobile/location', data);
    return response.data;
  },

  /**
   * Busca dados de regiões de surto para exibição visual (Mapa de Calor).
   * Realiza a transformação dos dados brutos do backend para o formato da interface.
   * @returns Retorna um objeto OutbreakRegion ou null se não houver dados válidos.
   */
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

  /**
   * Verifica se uma coordenada específica está dentro de uma zona de risco.
   * Endpoint leve que não persiste dados no banco, apenas consulta.
   * @param latitude Latitude atual
   * @param longitude Longitude atual
   */
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