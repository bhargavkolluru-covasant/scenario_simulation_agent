# direct_test.py

import asyncio
import httpx


async def main():

    url = (
        "https://ariia-platform-ui-v2-trg-273497745552."
        "us-central1.run.app/health"
    )
    
    async with httpx.AsyncClient() as client:

        response = await client.get(url)

        print("Status:", response.status_code)
        print("Body:", response.text)


asyncio.run(main())