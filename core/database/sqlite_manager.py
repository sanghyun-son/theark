"""SQLite database manager implementation."""

import sqlite3

from core.database.sqlite_base import BaseSQLiteManager


class SQLiteManager(BaseSQLiteManager):
    """SQLite database manager implementation."""

    def create_tables(self) -> None:
        """Create all necessary database tables."""
        # Define schema as individual statements
        statements = [
            # 1) 논문
            """CREATE TABLE IF NOT EXISTS paper (
                paper_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id        TEXT NOT NULL UNIQUE,
                latest_version  INTEGER NOT NULL DEFAULT 1,
                title           TEXT NOT NULL,
                abstract        TEXT NOT NULL,
                primary_category TEXT NOT NULL,
                categories      TEXT NOT NULL,
                authors         TEXT NOT NULL,
                url_abs         TEXT NOT NULL,
                url_pdf         TEXT,
                published_at    TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )""",
            # 2) 요약
            """CREATE TABLE IF NOT EXISTS summary (
                summary_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id      INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
                version       INTEGER NOT NULL,
                overview      TEXT NOT NULL,
                motivation    TEXT NOT NULL,
                method        TEXT NOT NULL,
                result        TEXT NOT NULL,
                conclusion    TEXT NOT NULL,
                language      TEXT NOT NULL,
                interests     TEXT NOT NULL,
                relevance     INTEGER NOT NULL,
                model         TEXT,
                is_read       BOOLEAN NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (paper_id, version, language)
            )""",  # noqa: E501
            # 3) 사용자
            """CREATE TABLE IF NOT EXISTS app_user (
                user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                email        TEXT NOT NULL UNIQUE,
                display_name TEXT
            )""",
            # 4) 사용자 관심사
            """CREATE TABLE IF NOT EXISTS user_interest (
                user_id   INTEGER NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                kind      TEXT NOT NULL,
                value     TEXT NOT NULL,
                weight    REAL NOT NULL DEFAULT 1.0,
                PRIMARY KEY (user_id, kind, value)
            )""",  # noqa: E501
            # 5) 사용자 즐겨찾기
            """CREATE TABLE IF NOT EXISTS user_star (
                user_id     INTEGER NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                paper_id    INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
                note        TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, paper_id)
            )""",  # noqa: E501
            # 6) 피드 아이템
            """CREATE TABLE IF NOT EXISTS feed_item (
                feed_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                paper_id     INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
                score        REAL NOT NULL,
                feed_date    TEXT NOT NULL,
                created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, paper_id, feed_date)
            )""",  # noqa: E501
            # 7) 크롤 이벤트
            """CREATE TABLE IF NOT EXISTS crawl_event (
                event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id     TEXT,
                event_type   TEXT NOT NULL,
                detail       TEXT,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            )""",  # noqa: E501
            # 8) 인덱스들
            """CREATE INDEX IF NOT EXISTS idx_paper_published_at
                ON paper(published_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_paper_primary_category
                ON paper(primary_category)""",
            """CREATE INDEX IF NOT EXISTS idx_user_star_user
                ON user_star(user_id, created_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_summary_paper
                ON summary(paper_id, language)""",
        ]

        try:
            for statement in statements:
                self.execute(statement)

            self.logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise
