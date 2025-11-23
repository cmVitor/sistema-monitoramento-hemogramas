"""
Socket.IO Manager para comunicação em tempo real escalável.

Usa Socket.IO com Redis adapter para permitir múltiplas instâncias do servidor
e comunicação pub/sub entre elas.
"""
import logging
from typing import Dict, Set
import socketio
from ..core.config import settings
from .redis_service import redis_service

logger = logging.getLogger(__name__)


# Criar servidor Socket.IO com Redis adapter para escalabilidade
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False
)


class SocketIOManager:
    """
    Gerenciador de conexões Socket.IO para comunicação em tempo real.
    """

    def __init__(self):
        self.connected_users: Dict[str, str] = {}  # {sid: user_id}
        self.user_sessions: Dict[str, Set[str]] = {}  # {user_id: {sid1, sid2, ...}}

    async def initialize(self):
        """Inicializa conexão com Redis para pub/sub."""
        try:
            # Conectar Redis service
            await redis_service.connect()

            # Configurar Redis adapter para Socket.IO (permite escalar horizontalmente)
            mgr = socketio.AsyncRedisManager(settings.redis_url)
            sio.client_manager = mgr

            logger.info("✅ Socket.IO Manager inicializado com Redis adapter")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Socket.IO Manager: {e}")
            raise

    def register_user(self, sid: str, user_id: str):
        """
        Registra uma conexão de usuário.

        Args:
            sid: Session ID do Socket.IO
            user_id: ID do usuário/dispositivo
        """
        self.connected_users[sid] = user_id

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(sid)

        logger.info(f"👤 Usuário conectado: {user_id} (sid: {sid[:8]}...)")
        logger.info(f"📊 Total de conexões: {len(self.connected_users)}")

    def unregister_user(self, sid: str):
        """
        Remove registro de uma conexão.

        Args:
            sid: Session ID do Socket.IO
        """
        user_id = self.connected_users.pop(sid, None)

        if user_id and user_id in self.user_sessions:
            self.user_sessions[user_id].discard(sid)

            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]

        if user_id:
            logger.info(f"👤 Usuário desconectado: {user_id} (sid: {sid[:8]}...)")
            logger.info(f"📊 Total de conexões: {len(self.connected_users)}")

    def get_user_id(self, sid: str) -> str:
        """Retorna o user_id associado a uma sessão."""
        return self.connected_users.get(sid)

    def get_user_sessions(self, user_id: str) -> Set[str]:
        """Retorna todas as sessões ativas de um usuário."""
        return self.user_sessions.get(user_id, set())

    async def emit_to_user(self, user_id: str, event: str, data: dict):
        """
        Envia evento para todas as sessões de um usuário específico.

        Args:
            user_id: ID do usuário
            event: Nome do evento
            data: Dados a serem enviados
        """
        sessions = self.get_user_sessions(user_id)
        for sid in sessions:
            try:
                await sio.emit(event, data, room=sid)
            except Exception as e:
                logger.error(f"❌ Erro ao enviar para {user_id}: {e}")

    async def emit_to_nearby_users(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        event: str,
        data: dict,
        exclude_user: str = None
    ):
        """
        Envia evento para usuários próximos a uma localização.

        Args:
            latitude: Latitude central
            longitude: Longitude central
            radius_km: Raio de busca em km
            event: Nome do evento
            data: Dados a serem enviados
            exclude_user: ID de usuário para excluir do envio
        """
        try:
            nearby = await redis_service.get_nearby_users(
                latitude,
                longitude,
                radius_km
            )

            for user_data in nearby:
                user_id = user_data['user_id']

                if user_id != exclude_user:
                    await self.emit_to_user(user_id, event, data)

            logger.info(f"📢 Evento '{event}' enviado para {len(nearby)} usuários próximos")

        except Exception as e:
            logger.error(f"❌ Erro ao enviar para usuários próximos: {e}")

    async def broadcast(self, event: str, data: dict):
        """
        Envia evento para TODOS os clientes conectados.

        Args:
            event: Nome do evento
            data: Dados a serem enviados
        """
        try:
            await sio.emit(event, data)
            logger.info(f"📢 Broadcast enviado: {event}")
        except Exception as e:
            logger.error(f"❌ Erro no broadcast: {e}")


# Instância global do manager
socketio_manager = SocketIOManager()


# ========== Event Handlers ==========

@sio.event
async def connect(sid, environ):
    """Handler de conexão inicial."""
    logger.info(f"🔌 Nova conexão Socket.IO: {sid[:8]}...")


@sio.event
async def disconnect(sid):
    """Handler de desconexão."""
    socketio_manager.unregister_user(sid)
    logger.info(f"🔌 Desconexão Socket.IO: {sid[:8]}...")


@sio.event
async def authenticate(sid, data):
    """
    Autentica usuário e registra a sessão.

    Payload esperado:
    {
        "user_id": "device-id-123"
    }
    """
    try:
        user_id = data.get('user_id')

        if not user_id:
            await sio.emit('error', {'message': 'user_id é obrigatório'}, room=sid)
            return

        socketio_manager.register_user(sid, user_id)

        await sio.emit('authenticated', {
            'status': 'success',
            'user_id': user_id
        }, room=sid)

    except Exception as e:
        logger.error(f"❌ Erro na autenticação: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def update_location(sid, data):
    """
    Recebe atualização de localização do cliente.

    Payload esperado:
    {
        "latitude": -23.550520,
        "longitude": -46.633308,
        "timestamp": "2025-01-15T10:30:00Z"
    }
    """
    try:
        user_id = socketio_manager.get_user_id(sid)

        if not user_id:
            await sio.emit('error', {'message': 'Usuário não autenticado'}, room=sid)
            return

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is None or longitude is None:
            await sio.emit('error', {'message': 'latitude e longitude são obrigatórios'}, room=sid)
            return

        # Salvar localização no Redis
        await redis_service.save_user_location(
            user_id,
            latitude,
            longitude,
            ttl_seconds=600  # 10 minutos
        )

        # Publicar update no Redis pub/sub
        await redis_service.publish_location_update(user_id, {
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': data.get('timestamp')
        })

        # Confirmar recebimento
        await sio.emit('location_updated', {
            'status': 'success',
            'user_id': user_id
        }, room=sid)

        logger.debug(f"📍 Localização atualizada via Socket.IO: {user_id}")

    except Exception as e:
        logger.error(f"❌ Erro ao processar localização: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def get_nearby_users(sid, data):
    """
    Busca usuários próximos à localização do cliente.

    Payload esperado:
    {
        "latitude": -23.550520,
        "longitude": -46.633308,
        "radius_km": 5.0
    }
    """
    try:
        user_id = socketio_manager.get_user_id(sid)

        if not user_id:
            await sio.emit('error', {'message': 'Usuário não autenticado'}, room=sid)
            return

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        radius_km = data.get('radius_km', 5.0)

        nearby = await redis_service.get_nearby_users(
            latitude,
            longitude,
            radius_km
        )

        await sio.emit('nearby_users', {
            'users': nearby,
            'count': len(nearby)
        }, room=sid)

    except Exception as e:
        logger.error(f"❌ Erro ao buscar usuários próximos: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def ping(sid, data):
    """Handler de ping para manter conexão viva."""
    await sio.emit('pong', {'timestamp': data.get('timestamp')}, room=sid)
