import asyncio

from app.clients.health_client \
    import HealthClient


async def main():

    client = HealthClient(
        "http://localhost:8000"
    )

    response = await client.health()

    print(response)


if __name__ == "__main__":
    asyncio.run(main())