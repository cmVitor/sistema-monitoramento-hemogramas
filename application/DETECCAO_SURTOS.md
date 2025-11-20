# Detecção e Delimitação de Surtos

Este documento descreve como o sistema identifica surtos epidemiológicos e delimita suas áreas geográficas.

---

## 1. Detecção de Surtos

### 1.1 Critérios de Detecção

Um **surto é detectado** quando uma região atende **AMBOS** os critérios simultaneamente:

1. **Critério de Severidade**: >40% dos casos com leucócitos elevados (nos últimos 7 dias)
2. **Critério de Crescimento**: >20% de aumento no número de casos (últimas 24h vs 24h anteriores)

### 1.2 Threshold de Leucócitos Elevados

```
Leucócitos >= 11.000/µL = Elevado
```

**Fonte**: `application/src/utils/fhir_utils.py:9`

---

## 2. Janelas Temporais

O sistema utiliza três janelas temporais para análise:

| Janela | Período | Uso |
|--------|---------|-----|
| **7 dias** | Últimos 7 dias | Cálculo de estatísticas gerais e percentual de casos elevados |
| **Últimas 24h** | Últimas 24 horas | Contagem de casos recentes |
| **24h anteriores** | De 48h até 24h atrás | Contagem de casos do período anterior (para calcular aumento) |

---

## 3. Cálculo de Estatísticas

Para cada região, o sistema calcula:

### 3.1 Total de Casos (7 dias)
```sql
SELECT COUNT(*)
FROM hemogram_observations
WHERE region_ibge_code = 'XXXXX'
  AND received_at >= NOW() - INTERVAL '7 days'
```

### 3.2 Casos com Leucócitos Elevados (7 dias)
```sql
SELECT COUNT(*)
FROM hemogram_observations
WHERE region_ibge_code = 'XXXXX'
  AND received_at >= NOW() - INTERVAL '7 days'
  AND leukocytes >= 11000
```

### 3.3 Percentual de Casos Elevados
```
% Elevados = (Casos Elevados / Total de Casos) × 100
```

### 3.4 Casos nas Últimas 24h
```sql
SELECT COUNT(*)
FROM hemogram_observations
WHERE region_ibge_code = 'XXXXX'
  AND received_at >= NOW() - INTERVAL '24 hours'
```

### 3.5 Casos nas 24h Anteriores
```sql
SELECT COUNT(*)
FROM hemogram_observations
WHERE region_ibge_code = 'XXXXX'
  AND received_at >= NOW() - INTERVAL '48 hours'
  AND received_at < NOW() - INTERVAL '24 hours'
```

### 3.6 Percentual de Aumento
```
% Aumento = ((Últimas 24h - 24h Anteriores) / 24h Anteriores) × 100
```

**Caso especial**: Se não houver casos nas 24h anteriores, mas houver nas últimas 24h, considera-se 100% de aumento.

---

## 4. Lógica de Decisão

```python
def é_surto(estatísticas):
    return (
        estatísticas['pct_elevated'] > 40.0
        AND
        estatísticas['increase_24h_pct'] > 20.0
    )
```

**Arquivo**: `application/src/services/analysis.py:78`

### Exemplo de Surto Detectado

```
Região: 5208707 (Goiânia)
├─ Total de casos (7d): 450
├─ Casos elevados (7d): 225
├─ % Elevados: 50.0%          ✓ (> 40%)
├─ Casos últimas 24h: 120
├─ Casos 24h anteriores: 80
└─ % Aumento: 50.0%            ✓ (> 20%)

RESULTADO: SURTO DETECTADO ⚠️
```

---

## 5. Delimitação Geográfica da Área de Surto

Quando um surto é detectado, o sistema calcula automaticamente a área geográfica afetada.

### 5.1 Coleta de Observações

O sistema busca **todas as observações com coordenadas** da região nos **últimos 7 dias**:

```sql
SELECT latitude, longitude
FROM hemogram_observations
WHERE region_ibge_code = 'XXXXX'
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND received_at >= NOW() - INTERVAL '7 days'
```

**Arquivo**: `application/src/services/geospatial.py:99-107`

---

### 5.2 Cálculo do Centroide

O **centroide** (centro geográfico) é calculado pela **média aritmética** de todas as coordenadas:

```python
centroide_latitude = Σ(latitudes) / n
centroide_longitude = Σ(longitudes) / n
```

Onde `n` = número total de observações com coordenadas.

**Arquivo**: `application/src/services/geospatial.py:14-33`

#### Exemplo

```
Observações:
- Ponto 1: (-16.680, -49.254)
- Ponto 2: (-16.682, -49.256)
- Ponto 3: (-16.678, -49.252)

Centroide:
- Latitude: (-16.680 + -16.682 + -16.678) / 3 = -16.680
- Longitude: (-49.254 + -49.256 + -49.252) / 3 = -49.254
```

---

### 5.3 Cálculo do Raio

O raio da área de surto é calculado em 3 etapas:

#### Etapa 1: Distância Euclidiana Máxima

Calcula a distância de **cada ponto** até o **centroide** e identifica a **distância máxima**:

```python
distância = √[(lat - centroide_lat)² + (lng - centroide_lng)²]
distância_máxima = max(todas_distâncias)
```

#### Etapa 2: Conversão para Metros

Converte graus para metros usando a aproximação:

```
1 grau ≈ 111 km = 111.000 metros
```

```python
raio_metros = distância_máxima × 111.000
```

#### Etapa 3: Margem de Segurança (+30%)

Adiciona uma **margem de segurança de 30%** para garantir que toda a área afetada seja coberta:

```python
raio_final = raio_metros × 1.3
```

**Arquivo**: `application/src/services/geospatial.py:36-64`

#### Exemplo Completo

```
Pontos:
- P1: (-16.680, -49.254)
- P2: (-16.690, -49.264)  ← ponto mais distante
- P3: (-16.678, -49.252)

Centroide: (-16.683, -49.257)

Distâncias:
- P1 → Centroide: 0.0042°
- P2 → Centroide: 0.0099°  ← máxima
- P3 → Centroide: 0.0071°

Cálculo do Raio:
1. Distância máxima: 0.0099°
2. Conversão: 0.0099 × 111.000 = 1.099 metros
3. Margem 30%: 1.099 × 1.3 = 1.429 metros

RESULTADO: Círculo com raio de 1.429m centrado em (-16.683, -49.257)
```

---

## 6. Representação Visual no Mapa

A área de surto é representada visualmente por:

1. **Círculo delimitador**:
   - Centro: Centroide calculado
   - Raio: Raio com margem de 30%
   - Estilo: Borda tracejada amarela, preenchimento gradiente escuro

2. **Marcadores individuais**:
   - Cada observação dentro da área é mostrada como ponto individual
   - Cor indica nível de leucócitos

3. **Label de alerta**:
   - Exibe "⚠️ SURTO - (X casos)" sobre a área
   - Número de casos = total de observações na região

**Arquivo**: `application/static/heatmap.html:736-820`

---

## 7. Atualização em Tempo Real

O sistema opera em tempo real:

- **Cada nova observação** dispara verificação de surto para a região
- **WebSocket** notifica clientes conectados instantaneamente
- **Detecção incremental** a cada 50 observações durante seed-data
- **Mapa atualiza automaticamente** ao receber notificação

**Arquivo**: `application/src/main.py:103-160` (endpoint POST /observations)

---

## 8. Alertas FHIR

Quando um surto é detectado, o sistema cria:

1. **Registro no banco**: Tabela `alerts` (AlertCommunication)
2. **Recurso FHIR Communication**: Seguindo padrão FHIR R4
3. **Notificação WebSocket**: Enviada para todos os clientes conectados
4. **Notificação do navegador**: Se permissões estiverem habilitadas

### Estrutura do Alerta

```json
{
  "id": 123,
  "region": "5208707",
  "summary": "Alerta de possível surto em 5208707: 50.0% com leucócitos elevados; aumento de 50.0% nas últimas 24h.",
  "created_at": "2024-01-15T10:30:00Z",
  "fhir_communication": {
    "resourceType": "Communication",
    "status": "completed",
    "category": "alert",
    ...
  }
}
```

---

## 9. Arquivos de Referência

| Funcionalidade | Arquivo | Linhas |
|----------------|---------|--------|
| Detecção de surtos | `src/services/analysis.py` | 72-94 |
| Cálculo de estatísticas | `src/services/analysis.py` | 10-69 |
| Cálculo de centroide | `src/services/geospatial.py` | 14-33 |
| Cálculo de raio | `src/services/geospatial.py` | 36-64 |
| Delimitação de área | `src/services/geospatial.py` | 67-144 |
| Threshold de leucócitos | `src/utils/fhir_utils.py` | 9 |
| Visualização no mapa | `static/heatmap.html` | 736-820 |
| WebSocket em tempo real | `src/services/websocket_manager.py` | 1-111 |

---

## 10. Resumo dos Parâmetros

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| **Threshold leucócitos** | ≥ 11.000/µL | Considera-se elevado |
| **Critério severidade** | > 40% | % de casos elevados |
| **Critério crescimento** | > 20% | % de aumento em 24h |
| **Janela estatísticas** | 7 dias | Período de análise geral |
| **Janela crescimento** | 24h vs 24h | Comparação recente |
| **Margem de segurança** | +30% | Adicional ao raio calculado |
| **Conversão grau→metro** | 1° ≈ 111km | Aproximação geográfica |
| **Intervalo tempo real** | 0.05s | Delay entre observações no seed |

---

**Última atualização**: 2024-01-19
**Sistema**: Ubiquo - Monitoramento de Hemogramas
