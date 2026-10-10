from datetime import datetime, timedelta

import aiosqlite

from app.config import DB_PATH
from app.healthcheck import is_alive

TOP_COMPANIES_LIMIT = 5


def _sqlite_timestamp(delta: timedelta) -> str:
    """Формат SQLite CURRENT_TIMESTAMP (используется в users.joined_at)."""
    return (datetime.utcnow() - delta).strftime("%Y-%m-%d %H:%M:%S")


def _iso_timestamp(delta: timedelta) -> str:
    """Формат, в котором сами пишем analysis_requests.created_at."""
    return (datetime.utcnow() - delta).isoformat()


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async def scalar(query: str, params: tuple = ()) -> int:
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
            return row[0] if row else 0

        total_users = await scalar("SELECT COUNT(*) FROM users")
        new_users_24h = await scalar(
            "SELECT COUNT(*) FROM users WHERE joined_at >= ?",
            (_sqlite_timestamp(timedelta(hours=24)),),
        )
        new_users_7d = await scalar(
            "SELECT COUNT(*) FROM users WHERE joined_at >= ?",
            (_sqlite_timestamp(timedelta(days=7)),),
        )

        total_requests = await scalar("SELECT COUNT(*) FROM analysis_requests")
        requests_24h = await scalar(
            "SELECT COUNT(*) FROM analysis_requests WHERE created_at >= ?",
            (_iso_timestamp(timedelta(hours=24)),),
        )
        requests_7d = await scalar(
            "SELECT COUNT(*) FROM analysis_requests WHERE created_at >= ?",
            (_iso_timestamp(timedelta(days=7)),),
        )
        active_users_7d = await scalar(
            "SELECT COUNT(DISTINCT user_id) FROM analysis_requests WHERE created_at >= ?",
            (_iso_timestamp(timedelta(days=7)),),
        )

        async with db.execute(
            """
            SELECT company_name, COUNT(*) AS cnt FROM analysis_requests
            GROUP BY company_name ORDER BY cnt DESC LIMIT ?
            """,
            (TOP_COMPANIES_LIMIT,),
        ) as cursor:
            top_companies = [(row["company_name"], row["cnt"]) for row in await cursor.fetchall()]

        async with db.execute(
            """
            SELECT analysis_type, COUNT(*) AS cnt FROM analysis_requests
            GROUP BY analysis_type ORDER BY cnt DESC
            """
        ) as cursor:
            requests_by_type = [(row["analysis_type"], row["cnt"]) for row in await cursor.fetchall()]

        cached_companies = await scalar("SELECT COUNT(*) FROM companies")
        active_subscriptions = await scalar(
            "SELECT COUNT(*) FROM subscriptions WHERE expires_at > ?",
            (datetime.utcnow().isoformat(),),
        )
        blocked_users = await scalar("SELECT COUNT(*) FROM users WHERE is_blocked = 1")

    return {
        "total_users": total_users,
        "new_users_24h": new_users_24h,
        "new_users_7d": new_users_7d,
        "total_requests": total_requests,
        "requests_24h": requests_24h,
        "requests_7d": requests_7d,
        "active_users_7d": active_users_7d,
        "top_companies": top_companies,
        "requests_by_type": requests_by_type,
        "cached_companies": cached_companies,
        "active_subscriptions": active_subscriptions,
        "blocked_users": blocked_users,
        "bot_alive": is_alive(),
    }
