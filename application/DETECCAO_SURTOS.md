# Detecção e Delimitação de Surtos

Este documento descreve como o sistema identifica surtos epidemiológicos usando clustering geográfico e delimita suas áreas.

---

## 1. Detecção de Surtos por Clustering Geográfico

### 1.1 Visão Geral do Algoritmo

O sistema detecta surtos automaticamente usando **clustering geográfico** ao invés de divisões administrativas. Isso permite identificar focos de doenças independentemente de fronteiras políticas.

**Algoritmo:**
1. Busca todas as observações dos últimos 7 dias com coordenadas geográficas
2. Agrupa observações em clusters usando uma grade geográfica (0.1° ≈ 11km)
3. Para cada cluster com pelo menos 20 observações, calcula estatísticas
4. Detecta surto se algum cluster atender aos critérios

### 1.2 Critérios de Detecção por Cluster

Um **surto é detectado** quando um cluster geográfico atende **TODOS** os critérios:

1. **Critério de Volume**: Pelo menos 20 observações no cluster
2. **Critério de Severidade**: >40% dos casos com leucócitos elevados (nos últimos 7 dias)
3. **Critério de Crescimento**: >20% de aumento no número de casos (últimas 24h vs 24h anteriores)

### 1.3 Threshold de Leucócitos Elevados

```
Leucócitos >= 11.000/µL = Elevado
```

**Fonte**: `application/src/utils/fhir_utils.py:9`

---

## 2. Clustering Geográfico

### 2.1 Grade de Agrupamento

O sistema divide o mapa em células de uma grade geográfica:

```python
grid_size = 0.1°  # Aproximadamente 11km x 11km
grid_lat = int(latitude / 0.1)
grid_lng = int(longitude / 0.1)
grid_cell = (grid_lat, grid_lng)
```

**Exemplo:**
```
Observação em (-16.680, -49.254):
- grid_lat = int(-16.680 / 0.1) = -166
- grid_lng = int(-49.254 / 0.1) = -492
- Célula: (-166, -492)

Observação em (-16.685, -49.258):
- Célula: (-166, -492)  ← Mesmo cluster!

Observação em (-15.680, -49.254):
- Célula: (-156, -492)  ← Cluster diferente
```

### 2.2 Tamanho da Grade

| Valor | Tamanho Aproximado | Uso |
|-------|-------------------|-----|
| 0.05° | ~5.5km | Clusters pequenos (áreas urbanas densas) |
| **0.1°** | **~11km** | **Padrão - balanceado** |
| 0.2° | ~22km | Clusters grandes (áreas rurais) |

**Arquivo**: `application/src/services/analysis.py:11-40`

---

## 3. Janelas Temporais

O sistema utiliza três janelas temporais para análise:

| Janela | Período | Uso |
|--------|---------|-----|
| **7 dias** | Últimos 7 dias | Cálculo de estatísticas gerais e percentual de casos elevados |
| **Últimas 24h** | Últimas 24 horas | Contagem de casos recentes |
| **24h anteriores** | De 48h até 24h atrás | Contagem de casos do período anterior (para calcular aumento) |

---

## 4. Cálculo de Estatísticas por Cluster

Para cada cluster geográfico, o sistema calcula:

### 4.1 Total de Casos no Cluster (7 dias)
```python
# Filtra observações do cluster nos últimos 7 dias
obs_7d = [obs for obs in cluster if obs.received_at >= since_7d]
total = len(obs_7d)
```

### 4.2 Casos com Leucócitos Elevados (7 dias)
```python
elevated = sum(
    1 for obs in obs_7d
    if obs.leukocytes is not None and obs.leukocytes >= 11000
)
```

### 4.3 Percentual de Casos Elevados
```
% Elevados = (Casos Elevados / Total de Casos) × 100
```

### 4.4 Casos nas Últimas 24h
```python
last_24 = sum(1 for obs in obs_7d if obs.received_at >= since_24h)
```

### 4.5 Casos nas 24h Anteriores
```python
prev_24 = sum(
    1 for obs in obs_7d
    if since_prev_24h <= obs.received_at < since_24h
)
```

### 4.6 Percentual de Aumento
```
% Aumento = ((Últimas 24h - 24h Anteriores) / 24h Anteriores) × 100
```

**Caso especial**: Se não houver casos nas 24h anteriores, mas houver nas últimas 24h, considera-se 100% de aumento.

**Arquivo**: `application/src/services/analysis.py:43-101`

---

## 5. Lógica de Decisão

```python
def é_surto_no_cluster(cluster, estatísticas):
    return (
        len(cluster) >= 20  # Volume mínimo
        AND
        estatísticas['pct_elevated'] > 40.0  # Severidade
        AND
        estatísticas['increase_24h_pct'] > 20.0  # Crescimento
    )
```

**Arquivo**: `application/src/services/analysis.py:104-199`

### Exemplo de Surto Detectado

```
Cluster Geográfico (-166, -492) [Goiânia, GO]
├─ Observações totais: 450
├─ Volume: 450 casos        ✓ (>= 20)
├─ Casos elevados: 225
├─ % Elevados: 50.0%        ✓ (> 40%)
├─ Últimas 24h: 120
├─ 24h anteriores: 80
└─ % Aumento: 50.0%         ✓ (> 20%)

Centroide: (-16.6830, -49.2540)

RESULTADO: SURTO DETECTADO ⚠️
```

### Múltiplos Clusters

Se múltiplos clusters atendem aos critérios, o sistema seleciona o cluster com **maior percentual de casos elevados**.

---

## 6. Delimitação Geográfica da Área de Surto

Quando um surto é detectado, o sistema calcula automaticamente a área geográfica afetada.

### 6.1 Coleta de Observações do Cluster

O sistema usa **todas as observações do cluster com surto detectado** nos **últimos 7 dias**.

---

### 6.2 Cálculo do Centroide

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

### 6.3 Cálculo do Raio

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

## 7. Representação Visual no Mapa

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
   - Número de casos = total de observações

**Arquivo**: `application/static/heatmap.html:736-820`

---

## 8. Atualização em Tempo Real

O sistema opera em tempo real:

- **Cada nova observação** dispara verificação de surto
- **WebSocket** notifica clientes conectados instantaneamente
- **Detecção incremental** a cada 50 observações durante seed-data
- **Mapa atualiza automaticamente** ao receber notificação

**Arquivo**: `application/src/main.py:103-160` (endpoint POST /observations)

---

## 9. Alertas FHIR

Quando um surto é detectado, o sistema cria:

1. **Registro no banco**: Tabela `alerts` (AlertCommunication)
2. **Recurso FHIR Communication**: Seguindo padrão FHIR R4
3. **Notificação WebSocket**: Enviada para todos os clientes conectados
4. **Notificação do navegador**: Se permissões estiverem habilitadas

### Estrutura do Alerta

```json
{
  "id": 123,
  "summary": "Alerta de possivel surto detectado: 450 casos identificados, 50.0% com leucocitos elevados, aumento de 50.0% nas ultimas 24h. Localizacao: (-16.6830, -49.2540)",
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

## 10. Arquivos de Referência

| Funcionalidade | Arquivo | Linhas |
|----------------|---------|--------|
| **Clustering geográfico** | `src/services/analysis.py` | 11-40 |
| **Cálculo de estatísticas por cluster** | `src/services/analysis.py` | 43-101 |
| **Detecção de surtos** | `src/services/analysis.py` | 104-199 |
| Cálculo de centroide | `src/services/geospatial.py` | 14-33 |
| Cálculo de raio | `src/services/geospatial.py` | 36-64 |
| Delimitação de área | `src/services/geospatial.py` | 67-136 |
| Threshold de leucócitos | `src/utils/fhir_utils.py` | 9 |
| Visualização no mapa | `static/heatmap.html` | 736-820 |
| WebSocket em tempo real | `src/services/websocket_manager.py` | 1-111 |

---

## 11. Resumo dos Parâmetros

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| **Threshold leucócitos** | ≥ 11.000/µL | Considera-se elevado |
| **Tamanho da grade** | 0.1° (~11km) | Tamanho das células de clustering |
| **Volume mínimo** | ≥ 20 obs | Mínimo de observações por cluster |
| **Critério severidade** | > 40% | % de casos elevados no cluster |
| **Critério crescimento** | > 20% | % de aumento em 24h no cluster |
| **Janela estatísticas** | 7 dias | Período de análise geral |
| **Janela crescimento** | 24h vs 24h | Comparação recente |
| **Margem de segurança** | +30% | Adicional ao raio calculado |
| **Conversão grau→metro** | 1° ≈ 111km | Aproximação geográfica |
| **Intervalo tempo real** | 0.05s | Delay entre observações no seed |

---

**Última atualização**: 2024-01-19
**Sistema**: Ubiquo - Monitoramento de Hemogramas
