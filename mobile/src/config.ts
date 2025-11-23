// IP da sua máquina na rede local
// Para dispositivo físico: use o IP da sua máquina (descoberto com ipconfig/ifconfig)
// Para Android Emulator: use 10.0.2.2
// Para iOS Simulator: use localhost
export const API_BASE_URL = 'http://192.168.100.11:8000';

// Intervalo para ENVIAR localização completa ao servidor (atualiza BD)
export const LOCATION_UPDATE_INTERVAL = 10 * 60 * 1000; // 10 minutos (otimizado para reduzir carga no servidor)

// Intervalo para VERIFICAR zona de surto (endpoint leve, não atualiza BD)
export const OUTBREAK_CHECK_INTERVAL = 5 * 1000; // 30 segundos (detecção rápida)

export const LOCATION_MIN_DISTANCE = 20; // metros (mais sensível)
