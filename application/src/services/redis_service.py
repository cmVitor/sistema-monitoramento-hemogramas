"""
Redis Service para gerenciamento de localizações geoespaciais em tempo real.

Este serviço usa Redis para:
- Armazenar localizações de usuários com dados geoespaciais (GEOADD, GEORADIUS)
- Cache de dados voláteis com TTL automático
- Pub/Sub para notificações em tempo real
"""
import logging
from typing import List, Dict, Optional, Tuple
import redis.asyncio as redis
from ..core.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Serviço para gerenciar localizações de usuários e queries geoespaciais usando Redis.
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None

    async def connect(self):
        """Conecta ao Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"✅ Conectado ao Redis: {settings.redis_url}")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao Redis: {e}")
            raise

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis desconectado")

    async def save_user_location(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        ttl_seconds: int = 600  # 10 minutos por padrão
    ) -> bool:
        """
        Salva a localização de um usuário usando dados geoespaciais.

        Args:
            user_id: ID único do usuário/dispositivo
            latitude: Latitude da localização
            longitude: Longitude da localização
            ttl_seconds: Tempo de vida em segundos (padrão: 600s = 10min)

        Returns:
            bool: True se salvo com sucesso
        """
        try:
            # Adiciona localização ao índice geoespacial
            await self.redis_client.geoadd(
                "user_locations",
                (longitude, latitude, user_id)
            )

            # Salva metadados do usuário com TTL
            user_key = f"user:{user_id}"
            await self.redis_client.hset(
                user_key,
                mapping={
                    "latitude": str(latitude),
                    "longitude": str(longitude),
                    "last_update": str(int(redis.time.time()))
                }
            )
            await self.redis_client.expire(user_key, ttl_seconds)

            logger.debug(f"📍 Localização salva: {user_id} ({latitude:.6f}, {longitude:.6f})")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao salvar localização: {e}")
            return False

    async def get_nearby_users(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 100
    ) -> List[Dict[str, any]]:
        """
        Busca usuários próximos a uma localização usando GEORADIUS.

        Args:
            latitude: Latitude do ponto central
            longitude: Longitude do ponto central
            radius_km: Raio de busca em quilômetros
            limit: Número máximo de resultados

        Returns:
            Lista de usuários com suas distâncias
        """
        try:
            # Busca usuários dentro do raio
            results = await self.redis_client.georadius(
                "user_locations",
                longitude,
                latitude,
                radius_km,
                unit="km",
                withdist=True,
                withcoord=True,
                count=limit,
                sort="ASC"
            )

            nearby_users = []
            for user_id, distance, coords in results:
                nearby_users.append({
                    "user_id": user_id,
                    "distance_km": float(distance),
                    "latitude": coords[1],
                    "longitude": coords[0]
                })

            logger.debug(f"🔍 Encontrados {len(nearby_users)} usuários próximos")
            return nearby_users

        except Exception as e:
            logger.error(f"❌ Erro ao buscar usuários próximos: {e}")
            return []

    async def get_user_location(self, user_id: str) -> Optional[Dict[str, float]]:
        """
        Obtém a última localização conhecida de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Dict com latitude e longitude, ou None se não encontrado
        """
        try:
            user_key = f"user:{user_id}"
            data = await self.redis_client.hgetall(user_key)

            if data:
                return {
                    "latitude": float(data.get("latitude", 0)),
                    "longitude": float(data.get("longitude", 0)),
                    "last_update": int(data.get("last_update", 0))
                }
            return None

        except Exception as e:
            logger.error(f"❌ Erro ao buscar localização do usuário: {e}")
            return None

    async def remove_user_location(self, user_id: str) -> bool:
        """
        Remove a localização de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se removido com sucesso
        """
        try:
            # Remove do índice geoespacial
            await self.redis_client.zrem("user_locations", user_id)

            # Remove metadados
            user_key = f"user:{user_id}"
            await self.redis_client.delete(user_key)

            logger.debug(f"🗑️ Localização removida: {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao remover localização: {e}")
            return False

    async def get_all_active_users(self) -> List[str]:
        """
        Retorna lista de todos os usuários ativos (com localização).

        Returns:
            Lista de IDs de usuários
        """
        try:
            # ZRANGE retorna todos os membros do sorted set
            user_ids = await self.redis_client.zrange("user_locations", 0, -1)
            return user_ids

        except Exception as e:
            logger.error(f"❌ Erro ao buscar usuários ativos: {e}")
            return []

    async def get_users_count(self) -> int:
        """
        Retorna o número total de usuários ativos.

        Returns:
            Número de usuários
        """
        try:
            count = await self.redis_client.zcard("user_locations")
            return count

        except Exception as e:
            logger.error(f"❌ Erro ao contar usuários: {e}")
            return 0

    async def publish_location_update(self, user_id: str, data: dict):
        """
        Publica atualização de localização no canal Pub/Sub.

        Args:
            user_id: ID do usuário
            data: Dados da localização
        """
        try:
            import json
            channel = f"location_updates:{user_id}"
            await self.redis_client.publish(channel, json.dumps(data))
            logger.debug(f"📢 Publicado update de localização: {user_id}")

        except Exception as e:
            logger.error(f"❌ Erro ao publicar update: {e}")

    async def publish_broadcast(self, event_type: str, data: dict):
        """
        Publica evento broadcast para todos os clientes.

        Args:
            event_type: Tipo do evento (ex: 'outbreak_alert', 'system_notification')
            data: Dados do evento
        """
        try:
            import json
            channel = "broadcast_events"
            message = {
                "type": event_type,
                "data": data
            }
            await self.redis_client.publish(channel, json.dumps(message))
            logger.info(f"📢 Broadcast enviado: {event_type}")

        except Exception as e:
            logger.error(f"❌ Erro ao enviar broadcast: {e}")


# Instância global do serviço Redis
redis_service = RedisService()
