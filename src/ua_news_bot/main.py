import asyncio

from ua_news_bot.aggregator import fetch_all_latest
from ua_news_bot.dedup import SeenStore
from ua_news_bot.sources.suspilne import SuspilneSource


async def run() -> None:
    sources = [SuspilneSource()]

    # v1 dedup is optional; keeps output clean in case RSS repeats items
    items = await fetch_all_latest(
        sources,
        per_source_limit=50,
        dedup=SeenStore(),
    )

    print(f"Fetched total (after optional dedup): {len(items)}\n")
    for i, item in enumerate(items, start=1):
        print(f"{i}. [{item.source}] {item.title}")
        print(f"   {item.url}\n")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
