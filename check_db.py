#!/usr/bin/env python3
"""Check database for stored papers and their categories."""

import asyncio
from sqlmodel import Session, select

from core.database.engine import create_database_engine
from core.models.rows import Paper


async def check_database():
    """Check the database for stored papers."""
    engine = create_database_engine("sqlite:///db/theark.demo.db")

    with Session(engine) as session:
        papers = session.exec(select(Paper)).all()

        print(f"Total papers in database: {len(papers)}")
        print("\nPapers with their categories:")
        print("-" * 80)

        for paper in papers:
            print(f"ArXiv ID: {paper.arxiv_id}")
            print(f"Title: {paper.title[:60]}...")
            print(f"Primary Category: {paper.primary_category}")
            print(f"All Categories: {paper.categories}")
            print("-" * 80)


if __name__ == "__main__":
    asyncio.run(check_database())
