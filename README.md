# 📊 Sistema de Monitoramento de Hemogramas

Projeto desenvolvido para a disciplina **Software para Sistemas Ubíquos**, com objetivo de implementar um sistema capaz de receber, processar e analisar hemogramas em tempo real, detectando anomalias individuais e coletivas e notificando gestores de saúde pública.

---

## 👥 Integrantes da Equipe

-   👨‍💻 [Samuel Jose Evangelista Alves] - [202201712]
-   👨‍💻 [Vitor Martins Castanheira] - [202201717]
-   👨‍💻 [Guilherme Gonçalves Dutra de Mendonça] - [202201692]
-   👨‍💻 [Leonardo Ribeiro Oliveira Palmeira] - [202201701]

---

## 🚀 Objetivo
Permitir que gestores de saúde recebam, em tempo real, **alertas baseados em evidências laboratoriais populacionais**, a partir de hemogramas enviados por laboratórios da rede estadual.

---

## 🏗️ Arquitetura Geral
O sistema será composto por:

- **Receptor FHIR**: Recepção de hemogramas via mecanismo de subscription (FHIR R4, recurso `Observation`).  
- **Análise Individual**: Detecção de desvios hematológicos com base em valores de referência.  
- **Base Consolidada**: Armazenamento local dos hemogramas recebidos.  
- **Análise Coletiva**: Identificação de padrões anômalos populacionais em janelas deslizantes.  
- **API REST**: Disponibilização dos alertas gerados.  
- **Aplicativo Móvel (Android)**: Notificação push e consulta de alertas.  

---

## 📅 Marcos Técnicos

### 🔹 Marco 1 – Recepção FHIR
- Implementação do receptor de mensagens FHIR via subscription.  
- Parsing de instâncias do recurso **Observation (hemograma)**.  
- Exemplo de servidor de testes: [HAPI FHIR R4](https://hapi.fhir.org/baseR4/).  
---

### 🔹 Marco 2 – Análise Individual
- Componente de análise individual de hemogramas.  
- Detecção de desvios nos parâmetros hematológicos segundo tabela de referência:  

| Parâmetro   | Unidade | Valor Mínimo | Valor Máximo |
|-------------|---------|--------------|--------------|
| Leucócitos  | /µL     | 4.000        | 11.000       |
| Hemoglobina | g/dL    | 12.0         | 17.5         |
| Plaquetas   | /µL     | 150.000      | 450.000      |
| Hematócrito | %       | 36           | 52           |

- Qualquer valor fora da faixa será registrado como **alerta individual**.

---

### 🔹 Marco 3 – Base Consolidada
- Persistência dos hemogramas recebidos.  
- Estrutura de dados otimizada para consultas em janelas de tempo.  
- Banco de dados sugerido: **PostgreSQL** ou **MongoDB**.  

---

### 🔹 Marco 4 – Análise Coletiva
- Detecção de **padrões populacionais anômalos** em janelas deslizantes (ex.: últimas 24h).  
- Indicadores computados:  
- Total de hemogramas recebidos.  
- Proporção de exames com alertas individuais.  
- Média e desvio padrão dos parâmetros.  
- Tendência temporal (comparação com janela anterior).  
- Gatilhos para alerta coletivo:  
- Número mínimo de hemogramas.  
- Proporção de alertas acima do limiar configurado.  
- Aumento significativo em relação à janela anterior.  

---

## 🛠️ Tecnologias utilizadas (sujeito a mudanças)
- **Backend**: Java + Spring Boot  
- **FHIR**: [HAPI FHIR](https://hapifhir.io/)  
- **Banco de Dados**: PostgreSQL ou MongoDB  
- **API REST**: Spring Boot REST Controllers  
- **App Mobile**: React Native ou Flutter  
- **Notificações Push**: Firebase Cloud Messaging  

---

## 📲 Fluxo do Sistema
```mermaid
flowchart TD
  A[Laboratórios - FHIR Observation] -->|Subscription| B[Receptor FHIR - Spring Boot]
  B --> C[Base Consolidada - DB]
  C --> D[Análise Individual]
  C --> E[Análise Coletiva - Janelas Deslizantes]
  E --> F[Gerador de Alertas]
  F --> G[API REST - Spring Boot]
  G --> H[App Android - Notificações Push] 
```

## 📌 Status do Projeto (Cronograma)

| Sprint | Período        | Entregas Principais                                      | Status |
|--------|----------------|----------------------------------------------------------|--------|
| Sprint 1 | Setembro/2025 | Marco 1 – Recepção FHIR (Subscription + Parsing)      | ⬜ Pendente |
| Sprint 2 | Outubro/2025  | Marco 2 – Análise Individual (detecção de desvios)    | ⬜ Pendente |
| Sprint 3 | Novembro/2025 | Marco 3 – Base Consolidada (persistência dos dados)   | ⬜ Pendente |
| Sprint 4 | Dezembro/2025 | Marco 4 – Análise Coletiva (padrões populacionais)    | ⬜ Pendente |
| Sprint Final| Dezembro/2025 | Entrega Final - Apresentação do sistema completo, incluindo API, App Móvel e documentação final | ⬜ Pendente | 
Legenda: ⬜ Pendente | 🟨 Em andamento | ✅ Concluído



