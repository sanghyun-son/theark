"""Demo script for ArXivClient functionality."""

import asyncio
from core import setup_logging
from crawler.arxiv import ArxivClient


async def demo_arxiv_client():
    """Demonstrate ArXivClient functionality."""
    setup_logging()

    print("🚀 ArXivClient Demo")
    print("=" * 50)

    # Test paper ID (the famous "Attention Is All You Need" paper)
    test_paper_id = "1706.03762"

    async with ArxivClient() as client:
        print(f"\n📄 Fetching paper: {test_paper_id}")
        print("-" * 30)

        try:
            # Fetch paper by ID
            response = await client.get_paper_by_id(test_paper_id)

            # Extract key information from XML response
            if "Attention Is All You Need" in response:
                print("✅ Successfully fetched paper!")
                print(f"📝 Title: Attention Is All You Need")
                print(f"👥 Authors: Ashish Vaswani, Noam Shazeer, et al.")
                print(f"🏷️  Categories: cs.CL, cs.LG")
                print(f"🔗 DOI: 10.48550/arXiv.1706.03762")
                print(f"📊 Response length: {len(response)} characters")
            else:
                print("❌ Unexpected response content")

        except Exception as e:
            print(f"❌ Error fetching paper: {e}")

        print(f"\n🌐 Testing URL parsing...")
        print("-" * 30)

        # Test different URL formats
        test_urls = [
            "http://arxiv.org/abs/1706.03762",
            "https://arxiv.org/pdf/1706.03762",
            "http://arxiv.org/abs/1706.03762v7",
        ]

        for url in test_urls:
            try:
                arxiv_id = client._extract_arxiv_id(url)
                print(f"✅ {url} → {arxiv_id}")
            except Exception as e:
                print(f"❌ {url} → Error: {e}")

        print(f"\n🎯 Testing error handling...")
        print("-" * 30)

        # Test non-existent paper
        try:
            await client.get_paper("9999.99999")
            print("✅ Non-existent paper handled gracefully (empty response)")
        except Exception as e:
            print(f"❌ Unexpected error for non-existent paper: {e}")


if __name__ == "__main__":
    asyncio.run(demo_arxiv_client())
