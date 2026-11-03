from app.clients.base_client import BaseClient


class HealthClient(BaseClient):

    async def health(self):

        return await self.get(
            "/health"
        )