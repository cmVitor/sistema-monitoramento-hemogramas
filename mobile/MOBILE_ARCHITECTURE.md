# Arquitetura do Sistema Mobile de Alertas

## Visão Geral

Sistema escalável para alertar milhares de usuários mobile sobre regiões de surto em tempo real, sem usar WebSocket e com custo zero.

## Componentes

### 1. Mobile App (React Native + Expo)

**Responsabilidades:**
- Coletar localização do usuário em background
- Enviar localização para o backend periodicamente
- Receber e exibir notificações push

**Tecnologias:**
- React Native 0.73
- Expo 50
- expo-location (geolocalização)
- expo-notifications (push notifications)
- expo-task-manager (background tasks)

**Fluxo de Geolocalização:**
```
1. Usuário inicia monitoramento
2. App solicita permissões (Localização Always + Notificações)
3. Task Manager inicia monitoramento em background
4. A cada 5 min OU 100 metros de movimento:
   - Captura lat/lng
   - Envia POST /api/mobile/location
5. Se backend detectar surto, retorna flag
6. App recebe notificação push via Expo
```

### 2. Backend API (FastAPI)

**Novos Endpoints:**

#### POST /api/mobile/register
Registra dispositivo para receber alertas.
- Cria/atualiza registro em `mobile_devices`
- Armazena Expo Push Token
- Retorna confirmação

#### POST /api/mobile/location
Recebe atualização de localização.
- Valida device_id
- Atualiza `last_location_lat/lng` em `mobile_devices`
- Chama `mobile_location_service.update_device_location()`
- Verifica se está em zona de surto usando `compute_outbreak_regions()`
- Se entrou em zona de surto:
  - Envia notificação via `notification_service.send_outbreak_alert()`
  - Retorna `alert_sent: true`

#### POST /api/mobile/unregister/{device_id}
Remove dispositivo do monitoramento.

**Novos Serviços:**

#### `notification_service.py`
- **send_notification()**: Envia notificação para 1 dispositivo
- **send_batch_notifications()**: Envia para múltiplos (até 100 por request)
- **send_outbreak_alert()**: Envia alerta de surto formatado
- Usa Expo Push Notification API (https://exp.host/--/api/v2/push/send)
- Totalmente gratuito e ilimitado

#### `mobile_location_service.py`
- **is_in_outbreak_zone()**: Verifica se lat/lng está em zona de surto
- **update_device_location()**: Atualiza localização e detecta entrada em zona
- **get_devices_in_outbreak_zone()**: Lista todos dispositivos em zona de surto

**Novo Modelo:**

```python
class MobileDevice(Base):
    device_id: str           # Único identificador do dispositivo
    fcm_token: str           # Expo Push Token
    platform: str            # 'ios' ou 'android'
    last_location_lat: float # Última localização
    last_location_lng: float
    last_location_update: datetime
    is_active: bool          # Se está recebendo alertas
    registered_at: datetime
    updated_at: datetime
```

### 3. Sistema de Notificações (Expo Push Notifications)

**Por que Expo?**
- ✅ 100% gratuito (sem limites)
- ✅ Escalável (milhões de dispositivos)
- ✅ Simples (HTTP API)
- ✅ Não precisa de broker/mensageria
- ✅ Funciona iOS + Android

**Fluxo de Notificação:**
```
1. Backend detecta usuário em zona de surto
2. Backend faz HTTP POST para exp.host com token do usuário
3. Expo entrega notificação para Apple/Google
4. Apple/Google entregam para dispositivo
5. Usuário vê notificação
```

**Exemplo de Request:**
```json
POST https://exp.host/--/api/v2/push/send
{
  "to": "ExponentPushToken[xxxxxx]",
  "title": "⚠️ Alerta de Surto",
  "body": "Surto detectado em região próxima",
  "sound": "default",
  "priority": "high"
}
```

## Fluxo Completo de Funcionamento

### Registro Inicial
```
[Mobile]                [Backend]              [Database]
   |                        |                       |
   |-- POST /register ---->|                       |
   |   {device_id,          |                       |
   |    fcm_token}          |----> INSERT --------->|
   |                        |<----- OK ------------|
   |<--- 200 OK ------------|                       |
```

### Monitoramento Contínuo
```
[Mobile]                [Backend]                    [Expo]
   |                        |                           |
   |  (a cada 5min)         |                           |
   |-- POST /location ----->|                           |
   |   {lat, lng}           |                           |
   |                        |--- Check outbreak zone -->|
   |                        |                           |
   |                        |--- Se em zona de surto -->|
   |                        |                           |
   |                        |-- POST exp.host --------->|
   |                        |   {token, mensagem}       |
   |                        |                           |
   |<---------------------- Push Notification ---------|
   |  "⚠️ Alerta de Surto"  |                           |
```

## Otimizações de Escala

### Para Milhares de Dispositivos

1. **Batching de Notificações**
   - Backend agrupa até 100 tokens por request
   - Reduz latência e overhead de rede

2. **Índices de Banco**
   - `device_id` indexado para buscas rápidas
   - `last_location_update` indexado para queries temporais

3. **Cache de Regiões de Surto**
   - `compute_outbreak_regions()` pode ser cacheada (5-15 min)
   - Reduz carga no banco de dados

4. **Processamento Assíncrono**
   - Notificações enviadas de forma assíncrona
   - Não bloqueia resposta da API

### Limites e Performance

| Métrica | Valor |
|---------|-------|
| Dispositivos simultâneos | Ilimitado (Expo escala) |
| Requests de localização/min | ~12.000 (milhares/5min) |
| Notificações/min | Ilimitado (Expo) |
| Latência de alerta | 1-5 segundos |
| Custo mensal | $0 (Expo gratuito) |

## Comparação com Alternativas

### WebSocket (Não Recomendado)
❌ Mantém conexões abertas (sobrecarga)
❌ Difícil escalar para milhares
❌ Maior consumo de bateria no mobile
❌ Problema com reconexões

### MQTT + Broker (Ex: HiveMQ)
⚠️ HiveMQ free tier: 25 conexões simultâneas
⚠️ Precisa configurar broker
⚠️ Mais complexo que HTTP
✅ Bom para IoT, mas overkill aqui

### Firebase Cloud Messaging (FCM) Direto
✅ Gratuito e escalável
⚠️ Requer configuração Google/Apple
⚠️ Mais complexo de integrar
⚠️ Expo Push é wrapper sobre FCM/APNS

### Expo Push Notifications (Escolhido)
✅ Gratuito e ilimitado
✅ Abstrai FCM + APNS
✅ Simples (HTTP API)
✅ Funciona iOS + Android
✅ Sem configuração de certificados

## Segurança

### Autenticação
- `device_id` único por dispositivo
- Token regenerado a cada instalação
- Sem dados sensíveis no mobile

### Privacidade
- Localização não armazenada permanentemente no mobile
- Backend só armazena última localização
- Usuário pode desativar monitoramento

### Rate Limiting (Recomendado para Produção)
```python
# Adicionar em mobile.py
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/location")
@limiter.limit("60/minute")  # Max 60 updates por minuto por IP
async def update_location(...):
    ...
```

## Monitoramento e Observabilidade

### Métricas Importantes
- Dispositivos ativos: `GET /api/mobile/devices/count`
- Taxa de sucesso de notificações
- Latência de processamento de localização
- Taxa de entrada em zona de surto

### Logs
```python
# Backend já logga:
- Registros de dispositivos
- Atualizações de localização
- Envio de notificações
- Erros e exceções
```

## Testes

### Backend
```bash
# Testar registro
curl -X POST http://localhost:8000/api/mobile/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-1",
    "fcm_token": "ExponentPushToken[test]",
    "platform": "android"
  }'

# Testar localização
curl -X POST http://localhost:8000/api/mobile/location \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-1",
    "latitude": -23.5505,
    "longitude": -46.6333,
    "timestamp": "2024-01-15T10:30:00Z"
  }'
```

### Mobile
1. Teste em dispositivo físico (não emulador)
2. Verifique permissões concedidas
3. Monitore logs do Expo
4. Teste notificações

## Manutenção

### Limpeza de Dispositivos Inativos
```sql
-- Deletar dispositivos sem atualização há 30 dias
DELETE FROM mobile_devices
WHERE last_location_update < NOW() - INTERVAL '30 days';
```

### Atualização de Tokens
- Tokens Expo podem expirar
- App re-registra automaticamente ao abrir
- Backend atualiza token existente

## Futuras Melhorias

1. **Geofencing Nativo**
   - Usar geofencing do iOS/Android
   - Reduzir updates de localização

2. **Notificações Ricas**
   - Adicionar mapa na notificação
   - Botões de ação (Ver mapa, Ignorar)

3. **Múltiplas Zonas**
   - Detectar múltiplos surtos
   - Alertar sobre severidade

4. **Histórico de Alertas**
   - Armazenar no mobile
   - Exibir em timeline

5. **Analytics**
   - Taxa de conversão (notificação → ação)
   - Padrões de movimento
   - Eficácia de alertas
