
import asyncio
import httpx

from app.config.settings import settings


async def main():

    headers = {
        "Authorization":
            f"Bearer {settings.access_token}",

        "X-Scope-Id":
            settings.scope_id
    }

    async with httpx.AsyncClient() as client:

        response = await client.get(
            "https://ariia-data-ingestion-service-trg-273497745552.us-central1.run.app/api/v1/data-management/semantic-registry",
            headers=headers
        )

        print(response.status_code)
        print(response.text)

asyncio.run(main())