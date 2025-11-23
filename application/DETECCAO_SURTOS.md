# Detecção e Delimitação de Surtos Epidemiológicos

Este documento descreve em detalhes como o sistema Ubiquo identifica surtos epidemiológicos e delimita suas regiões geográficas afetadas.

---

## 1. Visão Geral do Processo

O sistema utiliza análise geoespacial avançada para detectar surtos de forma automática e contínua. A detecção ocorre independentemente de divisões administrativas, focando em padrões epidemiológicos reais observados através de hemogramas coletados. O processo é dividido em três etapas principais: agrupamento geográfico, análise temporal e delimitação espacial.

---

## 2. Coleta e Preparação dos Dados

### 2.1 Janela Temporal de Análise

O sistema trabalha com três janelas temporais distintas para análise epidemiológica. A primeira é a janela de 7 dias, que captura o comportamento geral do surto e serve como base para cálculos estatísticos abrangentes. A segunda é a janela de últimas 24 horas, que monitora a atividade mais recente e permite identificar acelerações no padrão de casos. A terceira é a janela de 24 horas anteriores, que compreende o período entre 48 e 24 horas atrás, utilizada como referência para calcular crescimento relativo.

### 2.2 Filtros de Qualidade

Apenas observações que contêm coordenadas geográficas válidas são consideradas na análise. O sistema requer latitude e longitude precisas para cada hemograma, descartando automaticamente registros sem geolocalização. Essa filtragem garante que todos os cálculos espaciais sejam baseados em dados confiáveis e geograficamente verificáveis.

---

## 3. Agrupamento Geográfico por Grade

### 3.1 Divisão em Células Geográficas

O sistema divide o território em células de uma grade geográfica uniforme. Cada célula tem tamanho de 0,2 graus, o que corresponde aproximadamente a 22 quilômetros. Esta divisão permite agrupar casos que ocorrem em proximidade geográfica sem depender de fronteiras municipais ou estaduais.

Cada observação é mapeada para uma célula específica através de suas coordenadas. Por exemplo, uma observação localizada em latitude -16,680 e longitude -49,254 é dividida por 0,2, resultando em índices inteiros que identificam sua célula na grade. Observações próximas compartilham a mesma célula, formando agrupamentos naturais.

### 3.2 Mesclagem de Células Adjacentes

Após a divisão inicial, o sistema identifica células vizinhas que devem ser consideradas parte do mesmo surto. Células são consideradas adjacentes quando estão a até uma posição de distância em qualquer direção, incluindo diagonais. Isso significa que uma célula pode ter até 8 vizinhas imediatas.

A mesclagem previne fragmentação artificial dos surtos. Um surto real pode se estender por múltiplas células adjacentes, e tratá-las separadamente geraria falsos negativos ou subestimaria a severidade do evento. Ao mesclar células próximas, o sistema reconstrói a extensão verdadeira do surto.

### 3.3 Exemplo Prático de Agrupamento

Considere três localizações de hemogramas: Hospital A em (-16,680, -49,254), Clínica B em (-16,685, -49,258) e Posto C em (-15,680, -49,254). O Hospital A e a Clínica B, apesar de estarem em endereços diferentes, caem na mesma célula da grade pois suas coordenadas divididas por 0,2 geram os mesmos índices. Já o Posto C cai em célula diferente, pois sua latitude está aproximadamente 1 grau distante.

Se o Hospital A e a Clínica B acumularem casos suficientes em sua célula, e o Posto C estiver em célula adjacente também com casos, o sistema pode mesclar ambas as células em um único cluster maior para análise conjunta.

---

## 4. Classificação de Surtos - Critérios de Detecção

### 4.1 Os Três Critérios Fundamentais

Um surto é detectado quando um cluster geográfico satisfaz simultaneamente três critérios rigorosos. Esses critérios foram estabelecidos para balancear sensibilidade e especificidade, evitando tanto falsos positivos quanto falsos negativos na detecção epidemiológica.

### 4.2 Critério 1 - Volume Mínimo de Casos

O primeiro critério exige que o cluster contenha pelo menos 20 observações nos últimos 7 dias. Este threshold elimina flutuações aleatórias e garante significância estatística. Clusters menores podem representar variações normais na demanda de exames ou casos isolados sem relevância epidemiológica.

O volume é calculado após filtrar para os últimos 7 dias, garantindo que apenas casos recentes sejam contabilizados. Observações mais antigas não contribuem para este critério, mantendo o foco em eventos atuais.

### 4.3 Critério 2 - Severidade por Leucócitos Elevados

O segundo critério analisa a severidade clínica dos casos. O sistema conta quantos hemogramas apresentam contagem de leucócitos igual ou superior a 11.000 células por microlitro, threshold clínico que indica resposta imune elevada. Um surto verdadeiro deve apresentar mais de 40% dos casos com leucócitos elevados nos últimos 7 dias.

Este critério diferencia surtos infecciosos reais de simples aumento no volume de exames. Se um cluster tem muitos hemogramas mas poucos casos elevados, não há evidência de processo infeccioso coletivo. O percentual de 40% foi calibrado para capturar surtos significativos sem disparar alertas para variações sazonais menores.

### 4.4 Critério 3 - Crescimento Temporal Acelerado

O terceiro critério verifica se há aceleração no padrão de casos. O sistema compara o número de casos nas últimas 24 horas com o número de casos nas 24 horas imediatamente anteriores. Um surto ativo deve mostrar crescimento superior a 20% nesta comparação.

Este critério temporal identifica surtos em expansão ativa. Situações endêmicas estáveis, mesmo com muitos casos, não disparam alertas pois não apresentam crescimento significativo. O sistema busca detectar eventos em evolução que requerem intervenção urgente.

Há um caso especial: quando existem casos nas últimas 24 horas mas nenhum caso nas 24 horas anteriores, o sistema considera crescimento de 100%, sinalizando início súbito de atividade epidemiológica.

### 4.5 Exemplo de Classificação Positiva

Imagine um cluster na região metropolitana de Goiânia. Nos últimos 7 dias, foram registradas 450 observações nesta área. Destas, 225 apresentam leucócitos elevados, representando 50% do total. Nas últimas 24 horas foram registrados 120 casos, enquanto nas 24 horas anteriores foram apenas 80 casos, indicando crescimento de 50%.

Este cluster satisfaz todos os critérios: volume de 450 casos supera os 20 mínimos, severidade de 50% excede os 40% requeridos, e crescimento de 50% ultrapassa os 20% necessários. O sistema classifica este cluster como surto ativo e gera alerta epidemiológico.

### 4.6 Exemplo de Classificação Negativa

Considere outro cluster em Brasília com 300 observações nos últimos 7 dias. Apenas 90 hemogramas mostram leucócitos elevados, representando 30% do total. Nas últimas 24 horas foram 65 casos, e nas 24 horas anteriores foram 62 casos, crescimento de apenas 4,8%.

Este cluster falha em dois critérios: severidade de 30% está abaixo dos 40% necessários, e crescimento de 4,8% não alcança os 20% mínimos. Apesar do volume substancial, o sistema não classifica como surto, interpretando como demanda normal de serviços de saúde sem padrão epidemiológico preocupante.

### 4.7 Seleção do Cluster Mais Severo

Quando múltiplos clusters satisfazem os critérios simultaneamente, o sistema seleciona aquele com maior percentual de casos elevados. Esta priorização garante que o alerta reflita a situação mais crítica observada. Apenas um surto é reportado por vez, evitando sobrecarga de alertas e focando atenção no evento mais severo.

---

## 5. Cálculo da Região Geográfica do Surto

### 5.1 Identificação das Observações do Surto

Uma vez detectado o surto e identificado o cluster crítico, o sistema coleta todas as observações geográficas deste cluster nos últimos 7 dias. Cada observação possui latitude e longitude precisas que serão utilizadas nos cálculos de delimitação espacial.

### 5.2 Cálculo do Centroide - Centro Geográfico

O centroide representa o ponto central geográfico do surto. É calculado através da média aritmética simples de todas as coordenadas. A latitude do centroide é a soma de todas as latitudes dividida pelo número de observações. A longitude do centroide segue o mesmo princípio.

Este cálculo produz o centro de massa geográfico da distribuição de casos. O centroide não necessariamente corresponde a um local onde houve caso específico, mas representa o ponto de equilíbrio espacial do conjunto de observações.

### 5.3 Exemplo de Cálculo de Centroide

Considere um surto com quatro observações: Ponto A em (-16,680, -49,254), Ponto B em (-16,682, -49,256), Ponto C em (-16,678, -49,252) e Ponto D em (-16,684, -49,258). A latitude do centroide será a soma das quatro latitudes dividida por quatro: (-16,680 - 16,682 - 16,678 - 16,684) / 4 = -16,681. A longitude do centroide será: (-49,254 - 49,256 - 49,252 - 49,258) / 4 = -49,255. O centroide está localizado em (-16,681, -49,255).

### 5.4 Cálculo do Raio - Extensão da Área Afetada

O raio determina o tamanho do círculo que delimitará a região do surto. O cálculo é realizado em três etapas sequenciais, cada uma com propósito específico para garantir cobertura adequada.

### 5.5 Etapa 1 - Distância Euclidiana Máxima

O sistema calcula a distância de cada observação até o centroide usando fórmula euclidiana básica. A distância entre um ponto e o centroide é a raiz quadrada da soma dos quadrados das diferenças de latitude e longitude. O sistema identifica qual observação está mais distante do centroide, e esta distância máxima serve como base para o raio.

### 5.6 Etapa 2 - Conversão de Graus para Metros

As coordenadas geográficas são expressas em graus, mas distâncias práticas precisam ser em unidades métricas. O sistema aplica conversão padrão onde 1 grau de latitude ou longitude correspone aproximadamente a 111 quilômetros ou 111.000 metros. Esta é uma aproximação válida para cálculos em escalas regionais.

A distância máxima encontrada em graus é multiplicada por 111.000, convertendo-a para metros. Este valor representa o raio mínimo que engloba todas as observações do surto.

### 5.7 Etapa 3 - Margem de Segurança

O raio em metros é então multiplicado por 1,3, adicionando margem de segurança de 30%. Esta margem compensa três fatores: imprecisão inerente às coordenadas GPS, aproximação da conversão de graus para metros, e possibilidade de casos não reportados nas bordas do surto.

A margem garante que a área delimitada seja conservadora, preferindo incluir área adicional a deixar possíveis casos não detectados fora da zona de alerta. Este buffer de segurança é prática epidemiológica padrão.

### 5.8 Exemplo Completo de Cálculo de Raio

Retomando o exemplo anterior com centroide em (-16,681, -49,255), vamos calcular as distâncias. Ponto A está a 0,0042 graus do centroide, Ponto B a 0,0014 graus, Ponto C a 0,0050 graus, e Ponto D a 0,0042 graus. A distância máxima é 0,0050 graus do Ponto C.

Convertendo para metros: 0,0050 × 111.000 = 555 metros. Aplicando margem de 30%: 555 × 1,3 = 722 metros. O raio final da região do surto é 722 metros.

### 5.9 Formato Geométrico - Círculo de Cobertura

A região do surto é representada como círculo perfeito centrado no centroide com o raio calculado. Esta simplificação geométrica facilita visualização e cálculos posteriores, como determinar se novos casos ou usuários estão dentro da zona afetada.

Embora surtos reais possam ter formatos irregulares seguindo rotas de transmissão, vias de transporte ou densidade populacional, o círculo fornece aproximação prática que engloba toda a área afetada com margem de segurança adequada.

---

## 6. Visualização e Representação no Mapa

### 6.1 Elementos Visuais da Região de Surto

No mapa interativo, a região de surto é exibida através de múltiplos elementos visuais complementares. Um círculo vermelho semi-transparente marca a área delimitada, permitindo ver características geográficas subjacentes. A borda do círculo é desenhada em vermelho sólido para contraste visual imediato.

Um marcador especial é posicionado exatamente no centroide calculado, indicando o epicentro geográfico do surto. Este marcador exibe informações resumidas quando clicado, incluindo número total de casos e percentual de severidade.

### 6.2 Pontos Individuais de Observação

Cada hemograma que compõe o surto é também representado como ponto individual dentro do círculo. Estes pontos são coloridos conforme o nível de leucócitos observado, permitindo visualizar a distribuição espacial da severidade dentro da região afetada.

### 6.3 Banner de Alerta

Um banner informativo é exibido no topo do mapa quando há surto ativo. O banner resume as estatísticas principais: número de casos, percentual de casos elevados, crescimento nas últimas 24 horas, e localização aproximada do centroide. Este banner permanece visível enquanto o surto atender aos critérios de detecção.

---

## 7. Verificação de Localização em Zona de Surto

### 7.1 Cálculo de Inclusão Geográfica

O sistema permite verificar se uma coordenada específica está dentro da zona de surto. Esta funcionalidade é essencial para alertas personalizados aos usuários do aplicativo móvel. O cálculo utiliza a mesma fórmula euclidiana de distância aplicada anteriormente.

Dada uma coordenada de teste, o sistema calcula sua distância até o centroide do surto. Se esta distância for menor ou igual ao raio calculado, a coordenada está dentro da zona afetada. Este teste geométrico simples é extremamente eficiente computacionalmente.

### 7.2 Notificações Móveis Baseadas em Localização

Quando usuários do aplicativo móvel enviam sua localização atualizada, o sistema verifica automaticamente se estão em zona de surto ativa. Usuários dentro da zona recebem notificação push imediata alertando sobre o risco epidemiológico local. Esta notificação inclui recomendações básicas de prevenção e informações sobre a situação atual.

---

## 8. Atualização Contínua e Tempo Real

### 8.1 Reavaliação Automática

O sistema reavalia a situação epidemiológica continuamente. Cada nova observação adicionada ao banco de dados dispara nova análise completa: reagrupamento geográfico, recálculo de estatísticas, reavaliação de critérios e, se necessário, atualização da região delimitada.

Esta abordagem garante que alertas reflitam sempre a situação mais atual. Se novos casos aparecem em área adjacente, o surto pode se expandir. Se casos diminuem e critérios não são mais satisfeitos, o alerta pode ser desativado automaticamente.

### 8.2 Comunicação via WebSocket

Quando a análise detecta mudança significativa - novo surto, expansão de região, ou resolução de surto - notificações são transmitidas instantaneamente via WebSocket para todos os clientes conectados. Mapas em navegadores e aplicativos móveis atualizam automaticamente sem necessidade de recarregar página ou fazer polling.

---

## 9. Considerações Técnicas e Limitações

### 9.1 Aproximações Geográficas

O sistema utiliza distância euclidiana simples e conversão linear de graus para metros. Estas são aproximações válidas para escalas regionais (até centenas de quilômetros) mas não consideram curvatura da Terra. Para áreas muito extensas ou em latitudes extremas, pode haver imprecisão marginal.

### 9.2 Dependência de Geolocalização

A detecção de surtos depende totalmente de observações com coordenadas válidas. Hemogramas sem geolocalização não contribuem para análise espacial, podendo resultar em subdetecção se grande parte dos dados não tiver coordenadas. A qualidade da detecção é diretamente proporcional à cobertura geográfica dos dados.

### 9.3 Calibração de Parâmetros

Os limiares utilizados (20 casos mínimos, 40% de severidade, 20% de crescimento, grade de 0,2 graus) foram definidos empiricamente para balancear sensibilidade e especificidade. Diferentes contextos epidemiológicos ou populacionais podem requerer ajustes destes parâmetros para otimização da detecção.

---

## 10. Resumo do Fluxo Completo

O processo completo de detecção e delimitação segue este fluxo: primeiro, coleta de todas as observações dos últimos 7 dias com coordenadas válidas. Segundo, divisão geográfica em grade de 0,2 graus. Terceiro, mesclagem de células adjacentes. Quarto, cálculo de estatísticas para cada cluster. Quinto, avaliação dos três critérios de surto. Sexto, seleção do cluster mais severo se múltiplos forem detectados. Sétimo, cálculo do centroide geográfico. Oitavo, cálculo do raio com margem de segurança. Nono, delimitação circular da região. Décimo, geração de alerta e notificações. Este ciclo se repete continuamente mantendo vigilância epidemiológica ativa.

---

## 11. Parâmetros de Configuração

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| Tamanho da grade de clustering | 0,2° (~22km) | Balanceia granularidade geográfica com robustez estatística |
| Volume mínimo de casos | 20 observações | Garante significância estatística, evita flutuações aleatórias |
| Threshold de leucócitos elevados | ≥ 11.000/µL | Padrão clínico para leucocitose indicando processo infeccioso |
| Critério de severidade | > 40% elevados | Diferencia surtos reais de variações normais na população |
| Critério de crescimento | > 20% em 24h | Identifica aceleração epidemiológica significativa |
| Janela de análise geral | 7 dias | Captura comportamento recente sem incluir eventos antigos |
| Janela de crescimento | 24h vs 24h | Detecta mudanças agudas no padrão de casos |
| Margem de segurança do raio | +30% | Compensa imprecisões e garante cobertura completa |
| Conversão graus para metros | 1° ≈ 111km | Aproximação padrão válida para escalas regionais |

---

**Documento atualizado**: 2025-11-23
**Sistema**: Ubiquo - Monitoramento Epidemiológico de Hemogramas
**Versão**: 2.0
