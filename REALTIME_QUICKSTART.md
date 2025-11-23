# Guia Rápido - Sistema Realtime com Redis + Socket.IO

## Início Rápido (5 minutos)

### 1. Iniciar Backend

```bash
cd sistema-monitoramento-hemogramas/application

# Iniciar todos os serviços (FastAPI + Redis + PostgreSQL)
docker-compose up --build

# Aguardar mensagem:
# ✅ Redis: Connected
# 🔌 Socket.IO: ws://localhost:8000/socket.io
```

### 2. Configurar Mobile

```bash
cd sistema-monitoramento-hemogramas/mobile

# Instalar dependências (se ainda não instalou)
npm install

# Descobrir seu IP local
# Windows: ipconfig
# Mac/Linux: ifconfig

# Editar src/config.ts
# Trocar para seu IP:

npm run setup-ip

# ou

export const API_BASE_URL = 'http://SEU_IP_AQUI:8000';

# Exemplo:
# export const API_BASE_URL = 'http://192.168.1.10:8000';
```

### 3. Iniciar App Mobile

```bash
npm start

# Escolher plataforma:
# - Pressione 'a' para Android
# - Pressione 'i' para iOS
# - Ou escaneie QR code com Expo Go
```

## Comandos Úteis

### Backend
```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Ver logs
docker-compose logs -f api

# Rebuild
docker-compose up --build

# Limpar volumes
docker-compose down -v

#Limpar banco
docker exec -it hemogram-postgres psql -U hemouser -d hemogram -c "TRUNCATE TABLE hemogram_observations, alerts, mobile_devices CASCADE;"
```

### Redis
```bash
# Conectar CLI
docker exec -it hemogram-redis redis-cli

# Ver todos os usuários
ZRANGE user_locations 0 -1

# Contar usuários
ZCARD user_locations

# Buscar próximos
GEORADIUS user_locations -46.633 -23.550 5 km WITHDIST

# Limpar dados
FLUSHDB
```

### Mobile
```bash
# Instalar
npm install

# Iniciar
npm start

# Limpar cache
npm start -- --clear

# Build produção
eas build --platform android
```
