# 🚀 Início Rápido - App Mobile

## ⚡ Setup em 3 Passos

### 1️⃣ Inicie o Backend
```bash
cd ../application
docker-compose up
```

Aguarde ver:
```
✓ Database tables created successfully
🚀 Hemogram Monitoring System Started
📍 API Docs: http://localhost:8000/docs
```

### 2️⃣ Configure o IP da API
```bash
npm run setup-ip
```

Ou edite manualmente `src/config.ts`:
```typescript
export const API_BASE_URL = 'http://192.168.100.11:8000'; // Seu IP aqui
```

### 3️⃣ Inicie o App
```bash
npm start
```

✅ Pronto! Escaneie o QR code com Expo Go

---

## 📱 No Celular

1. **Baixe o Expo Go**
   - iOS: App Store
   - Android: Play Store

2. **Conecte na mesma Wi-Fi**
   - Seu celular e computador devem estar na mesma rede

3. **Escaneie o QR Code**
   - iOS: Use a câmera nativa
   - Android: Use o Expo Go

4. **Conceda Permissões**
   - Localização: "Permitir sempre" ou "Quando usar o app"
   - Notificações: "Permitir"

5. **Inicie o Monitoramento**
   - Toque em "Iniciar Monitoramento"
   - Mantenha o app aberto (limitação Expo Go)

---

## ✅ Verificações

### Teste a Conexão
```bash
npm run check
```

Deve mostrar:
```
✅ Conexão bem-sucedida!
```

### Acesse no Navegador
```
http://192.168.100.11:8000/docs
```

Se abrir, está tudo certo! 🎉

---

## 🎯 Como Usar

### Interface Principal

```
┌─────────────────────────────────┐
│     Alerta de Surtos           │
│  Monitoramento em Tempo Real   │
├─────────────────────────────────┤
│ ℹ️ Modo Expo Go: Apenas         │
│    foreground                   │
├─────────────────────────────────┤
│ Status: ✓ Ativo / ○ Inativo    │
│ Última atualização: 10:30:15   │
├─────────────────────────────────┤
│ Localização Atual:              │
│ Lat: -23.550520                 │
│ Lng: -46.633308                 │
├─────────────────────────────────┤
│ [Iniciar Monitoramento]         │
│ [Ver Minha Localização]         │
└─────────────────────────────────┘
```

### Fluxo de Uso

1. **Primeira Vez:**
   - Toque "Iniciar Monitoramento"
   - Conceda permissões
   - App registra dispositivo
   - Começa a enviar localização

2. **Uso Normal:**
   - App verifica localização a cada 30 segundos
   - Se entrar em zona de surto:
     - 📱 Notificação local
     - ⚠️ Alert modal
     - 🔴 Status atualizado

3. **Ver Localização Atual:**
   - Toque "Ver Minha Localização"
   - Mostra coordenadas atuais
   - Não ativa monitoramento

4. **Parar Monitoramento:**
   - Toque "Parar Monitoramento"
   - Para de enviar localização
   - Mantém registro do dispositivo

---

## 🧪 Testando Alertas

### 1. Obtenha sua Localização
No app, toque em "Ver Minha Localização". Anote as coordenadas.

### 2. Crie um Surto
Abra: http://192.168.100.11:8000/docs

Vá para `POST /api/hemogram/outbreaks`

Use estas coordenadas:
```json
{
  "latitude": -23.550520,    // Sua latitude
  "longitude": -46.633308,   // Sua longitude
  "radius": 500,             // 500 metros de raio
  "severity": "high",
  "cases_count": 10,
  "description": "Surto de teste"
}
```

### 3. Aguarde a Detecção
- App verifica a cada 30 segundos
- Quando detectar, você receberá:
  - ⚠️ Notificação local
  - Alert modal no app
  - Status "Em zona de surto"

### 4. Limpe os Testes
Delete surtos criados em: `DELETE /api/hemogram/outbreaks/{id}`

---

## 📊 Monitorando Dados

### Ver no Backend

**Dispositivos Registrados:**
```
GET http://192.168.100.11:8000/api/mobile/devices/count
```

**Surtos Ativos:**
```
GET http://192.168.100.11:8000/api/hemogram/outbreaks
```

**Mapa de Calor:**
```
http://192.168.100.11:8000
```

### Ver no App

- Status: Ativo/Inativo
- Última atualização
- Coordenadas atuais
- Logs no console do Expo (pressione `j`)

---

## 🔄 Comandos Úteis

```bash
# Iniciar app
npm start

# Limpar cache
npm run clean

# Testar conexão
npm run check

# Configurar IP
npm run setup-ip

# Ver logs do backend
cd ../application && docker-compose logs -f api
```

---

## ⚠️ Limitações do Expo Go

### O que NÃO funciona:
- ❌ Background location (precisa manter app aberto)
- ❌ Push notifications remotas
- ❌ Monitoramento quando app está minimizado

### O que funciona:
- ✅ Foreground location
- ✅ Notificações locais
- ✅ Detecção de zonas de surto
- ✅ Registro de dispositivo
- ✅ Envio de localização para API

### Para Produção:
Crie um development build para ter todas as funcionalidades:
```bash
npx expo run:android
# ou
npx expo run:ios
```

---

## 🆘 Problemas?

### Erro de Conexão
```bash
npm run check
```
Veja [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

### Permissão Negada
Vá em: Configurações > Apps > Expo Go > Permissões

### App Não Atualiza
```bash
npm run clean
```

### Checklist:
- [ ] Backend rodando
- [ ] IP configurado corretamente
- [ ] Mesma rede Wi-Fi
- [ ] Permissões concedidas
- [ ] Expo Go atualizado

---

## 📖 Mais Informações

- [EXPO_GO_SETUP.md](./EXPO_GO_SETUP.md) - Configuração detalhada
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Resolução de problemas
- [MOBILE_ARCHITECTURE.md](./MOBILE_ARCHITECTURE.md) - Arquitetura do app

---

## 💡 Dicas

1. **Mantenha o app aberto** para monitoramento contínuo
2. **Use Wi-Fi estável** - dados móveis não funcionam
3. **Bateria** - Monitoramento GPS consome bateria
4. **Teste primeiro** - Use "Ver Localização" antes de iniciar monitoramento
5. **Logs** - Pressione `j` no Expo para ver console

---

## 🎉 Tudo Pronto!

Agora você pode:
- 📍 Monitorar sua localização
- 🚨 Receber alertas de surto
- 📊 Ver dados no backend
- 🗺️ Visualizar mapa de calor

Boa sorte! 🍀
