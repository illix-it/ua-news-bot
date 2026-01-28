import asyncio

from ua_news_bot.sources.suspilne import fetch_latest


async def run() -> None:
    items = await fetch_latest(limit=5)
    print(f"Fetched: {len(items)} items\n")

    for i, item in enumerate(items, start=1):
        print(f"{i}. [{item.source}] {item.title}")
        print(f"   {item.url}\n")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
