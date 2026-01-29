import asyncio
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session_maker
from app.db.models import Post, Media, User
from app.core.config import settings

ADMIN_EMAIL = "ab@yopmail.com"


async def delete_seeded_posts():
    async_session_maker = get_async_session_maker()

    async with async_session_maker() as session:
        # 1️⃣ Get admin user
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print(f"❌ Admin user {ADMIN_EMAIL} not found.")
            return

        # 2️⃣ Find seeded media
        media_result = await session.execute(
            select(Media.post_id)
            .where(Media.file_metadata["seed"].as_boolean() == True)
        )

        post_ids = {row[0] for row in media_result.fetchall()}

        if not post_ids:
            print("⚠️ No seeded posts found. Nothing to delete.")
            return

        print(f"🧹 Found {len(post_ids)} seeded posts. Deleting...")

        # 3️⃣ Delete Media first (FK safety)
        await session.execute(
            delete(Media).where(Media.post_id.in_(post_ids))
        )

        # 4️⃣ Delete Posts
        await session.execute(
            delete(Post)
            .where(Post.id.in_(post_ids))
            .where(Post.author_id == admin_user.id)
        )

        await session.commit()

        print(f"✅ Deleted {len(post_ids)} seeded posts successfully.")


if __name__ == "__main__":
    asyncio.run(delete_seeded_posts())
