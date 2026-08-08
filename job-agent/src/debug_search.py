import asyncio
import json

from mcp_linkedin_client import LinkedInMCPClient


async def main():
    async with LinkedInMCPClient() as client:
        result = await client.search_jobs(keywords="AI Product Manager", location="Bangalore")
        print(json.dumps(result, indent=2, default=str)[:3000])


if __name__ == "__main__":
    asyncio.run(main())
