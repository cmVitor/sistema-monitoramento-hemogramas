# 🚨 Sistema de Alertas Instantâneos

## ✅ Implementação Completa

O sistema foi completamente reformulado para fornecer **alertas INSTANTÂNEOS** quando você entra em uma zona de surto.

---

## ⚡ Melhorias Implementadas

### 1. **Verificação Ultra-Rápida**
- ⏱️ **Antes:** 30 segundos
- ⚡ **Agora:** 5 segundos
- 🎯 **Resultado:** 6x mais rápido

### 2. **Verificação Imediata ao Iniciar**
- ✅ Ao clicar "Iniciar Monitoramento"
- ✅ Verifica SUA LOCALIZAÇÃO ATUAL instantaneamente
- ✅ Se já está em zona de surto, alerta NA HORA

### 3. **Sistema de Notificações Urgentes**
- 📢 **Notificação local imediata** com prioridade MAX
- 🔔 **Vibração tripla** para chamar atenção
- 📱 **Alert modal** não cancelável com instruções
- 🔄 **Notificação de confirmação** após 2 segundos (backup)

### 4. **Feedback Visual Proeminente**
```
┌─────────────────────────────────┐
│  🚨                             │
│ VOCÊ ESTÁ EM ZONA DE SURTO!     │
│                                 │
│ Evite aglomerações e procure    │
│ orientação médica se necessário │
│                                 │
│ Alertas recebidos: 3            │
└─────────────────────────────────┘
```

- 🔴 **Banner vermelho** grande e visível
- 💡 **Sombra vermelha** para destacar
- 📊 **Contador de alertas** recebidos
- ⚠️ **Instruções claras** de segurança

---

## 🔄 Fluxo de Detecção

### Quando Você INICIA o Monitoramento:

```
1. Você clica "Iniciar Monitoramento"
   ↓
2. App pede permissões de localização
   ↓
3. ⚡ VERIFICA IMEDIATAMENTE sua localização
   ↓
4. Se está em zona de surto:
   • 🔴 Banner vermelho aparece
   • 📢 Notificação urgente
   • 🚨 Alert modal não cancelável
   • 🔔 Vibração
   ↓
5. Continua verificando a cada 5 segundos
```

### Durante o Monitoramento:

```
Verificação a cada 5 segundos:

📍 Pega localização atual
  ↓
🌐 Envia para API
  ↓
🔍 API verifica surtos próximos
  ↓
📊 Retorna: in_outbreak_zone: true/false
  ↓
Se true:
  • ⚡ Callback IMEDIATO
  • 🔴 Banner vermelho aparece
  • 📢 Notificações urgentes
  • 🚨 Alert modal
  • 🔔 Vibração
```

---

## 📱 Experiência do Usuário

### Cenário 1: Já Está em Zona de Surto

```
Você abre o app → Clica "Iniciar"
        ↓
    ⚡ IMEDIATO (0-2 segundos):
        • Alert modal: "ALERTA DE SURTO DETECTADO!"
        • Banner vermelho no app
        • Notificação + vibração
        • Instruções de segurança
```

### Cenário 2: Entra em Zona Durante Monitoramento

```
Você está caminhando com app aberto
        ↓
    A cada 5 segundos:
        • App verifica localização
        • Envia para API
        ↓
    Você entra em zona de surto
        ↓
    ⚡ Na próxima verificação (máx 5s):
        • Alert modal instantâneo
        • Banner vermelho
        • Notificações + vibração
        • Contador aumenta
```

---

## 🎯 Garantias de Detecção

### ✅ O que GARANTE alertas rápidos:

1. **Polling de 5 segundos**
   - Intervalo curto = detecção rápida
   - Máximo de 5 segundos para detectar

2. **Verificação imediata ao iniciar**
   - Se já está em surto = alerta instantâneo (0-2s)
   - Não precisa esperar primeiro ciclo

3. **Callback síncrono**
   - Resposta da API → Alerta imediato
   - Sem delays ou buffers

4. **Múltiplas formas de alerta**
   - Alert modal (não pode ignorar)
   - Notificação (fica na barra)
   - Banner visual (sempre visível)
   - Vibração (feedback tátil)

### ⚠️ Limitações do Expo Go:

- ❌ Não funciona com app em background
- ❌ Não funciona com app fechado
- ✅ Funciona perfeitamente com app aberto

---

## 🔍 Como Testar

### Teste 1: Já Está em Surto

1. Crie um surto na sua localização atual:
   ```
   POST http://192.168.100.11:8000/api/hemogram/outbreaks
   {
     "latitude": SUA_LAT,
     "longitude": SUA_LNG,
     "radius": 500,
     "severity": "high",
     "cases_count": 10
   }
   ```

2. No app:
   - Clique "Iniciar Monitoramento"
   - ⏱️ **Aguarde 1-2 segundos**
   - ✅ **Deve receber alerta IMEDIATO**

### Teste 2: Entrar em Zona

1. Inicie o monitoramento

2. Crie um surto próximo à sua localização

3. ⏱️ **Aguarde máximo 5 segundos**

4. ✅ **Deve receber alerta automaticamente**

### Teste 3: Múltiplos Alertas

1. Mantenha monitoramento ativo

2. Fique em zona de surto

3. Observe o contador aumentar a cada verificação

---

## 📊 Logs de Debug

Ao usar o app, você verá nos logs:

```
🚀 Iniciando monitoramento - Verificação imediata...
📍 Enviando localização: { lat: -23.550520, lng: -46.633308 }
✅ Resposta da API: {
  status: 'success',
  in_outbreak_zone: true,
  alert_sent: false
}
🚨 ALERTA: Você está em zona de surto!
🚨 Callback de surto acionado! inZone: true
📢 Enviando notificação local de alerta...
✅ Notificação enviada com sucesso!
🚨 Enviando alerta URGENTE de surto...
✅ Alertas urgentes enviados!
```

Para ver os logs:
- No terminal do Expo, pressione `j`
- Ou use React Native Debugger

---

## ⚙️ Configurações

### Ajustar Intervalo de Verificação

Edite `src/config.ts`:

```typescript
// Mais rápido (3 segundos) - Mais consumo de bateria
export const LOCATION_UPDATE_INTERVAL = 3 * 1000;

// Atual (5 segundos) - Balanceado
export const LOCATION_UPDATE_INTERVAL = 5 * 1000;

// Mais lento (10 segundos) - Economiza bateria
export const LOCATION_UPDATE_INTERVAL = 10 * 1000;
```

### Ajustar Sensibilidade

```typescript
// Mais sensível (10 metros)
export const LOCATION_MIN_DISTANCE = 10;

// Atual (20 metros)
export const LOCATION_MIN_DISTANCE = 20;

// Menos sensível (50 metros)
export const LOCATION_MIN_DISTANCE = 50;
```

---

## 🔋 Consumo de Bateria

### Estimativa de Impacto:

- **5 segundos:** Alto (recomendado para testes/emergências)
- **10 segundos:** Médio (bom balanceamento)
- **30 segundos:** Baixo (uso prolongado)

### Dicas para Economizar:

1. Use 10s para uso diário
2. Use 5s apenas em áreas de risco
3. Pause monitoramento quando não precisar
4. Mantenha tela ligada (necessário no Expo Go)

---

## ✅ Checklist de Funcionalidades

- [x] Polling de 5 segundos
- [x] Verificação imediata ao iniciar
- [x] Notificações locais urgentes
- [x] Alert modal não cancelável
- [x] Banner visual vermelho
- [x] Contador de alertas
- [x] Vibração tripla
- [x] Notificação de confirmação
- [x] Logs detalhados de debug
- [x] Instruções de segurança
- [x] Callback síncrono
- [x] Atualização de estado imediata

---

## 🎉 Resultado Final

Com essas melhorias, o sistema agora:

✅ **Detecta surtos em 5 segundos ou menos**
✅ **Alerta IMEDIATAMENTE ao iniciar se já está em zona**
✅ **Múltiplas formas de notificação simultâneas**
✅ **Feedback visual proeminente e impossível de ignorar**
✅ **Logs detalhados para debug**
✅ **Experiência de usuário otimizada**

---

## 🆘 Problemas?

Se não estiver recebendo alertas instantâneos:

1. **Verifique os logs** (pressione `j` no Expo)
2. **Confirme que está em zona de surto** (veja no mapa)
3. **Certifique-se que app está aberto** (Expo Go não funciona em background)
4. **Verifique permissões** de localização e notificações
5. **Teste a conexão** com `npm run check`

Veja [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) para mais detalhes.
