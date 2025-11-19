"""
WebSocket Manager para atualizações em tempo real do mapa de calor e alertas de surtos.
"""
import json
import logging
from typing import List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gerencia conexões WebSocket ativas e broadcast de mensagens.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """
        Aceita uma nova conexão WebSocket e adiciona à lista de conexões ativas.

        Args:
            websocket: Conexão WebSocket a ser adicionada
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nova conexão WebSocket estabelecida. Total de conexões: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove uma conexão WebSocket da lista de conexões ativas.

        Args:
            websocket: Conexão WebSocket a ser removida
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Conexão WebSocket encerrada. Total de conexões: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Envia uma mensagem para todas as conexões WebSocket ativas.
        Remove conexões que falharem no envio.

        Args:
            message: Dicionário com a mensagem a ser enviada (será convertido para JSON)
        """
        if not self.active_connections:
            logger.debug("Nenhuma conexão ativa para broadcast")
            return

        message_json = json.dumps(message)
        disconnected_clients = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem via WebSocket: {e}")
                disconnected_clients.append(connection)

        # Remove conexões que falharam
        for client in disconnected_clients:
            self.disconnect(client)

        if disconnected_clients:
            logger.warning(f"Removidas {len(disconnected_clients)} conexões inativas")

    async def send_new_observation_event(self, observation_data: dict):
        """
        Envia evento de nova observação para todos os clientes conectados.

        Args:
            observation_data: Dados da observação recém-criada
        """
        message = {
            "type": "new_observation",
            "data": observation_data
        }
        await self.broadcast(message)
        logger.info("Evento de nova observação enviado via WebSocket")

    async def send_outbreak_alert_event(self, alert_data: dict):
        """
        Envia evento de alerta de surto para todos os clientes conectados.

        Args:
            alert_data: Dados do alerta de surto
        """
        message = {
            "type": "outbreak_alert",
            "data": alert_data
        }
        await self.broadcast(message)
        logger.warning(f"Alerta de surto enviado via WebSocket para região {alert_data.get('region')}")

    async def send_data_refresh_event(self):
        """
        Envia evento solicitando atualização completa dos dados no cliente.
        Útil quando há mudanças significativas que exigem recarregamento completo.
        """
        message = {
            "type": "refresh_data",
            "data": {}
        }
        await self.broadcast(message)
        logger.info("Evento de atualização de dados enviado via WebSocket")


# Instância global do gerenciador de conexões
manager = ConnectionManager()
