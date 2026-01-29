import asyncio
from sqlalchemy import text
from app.db.session import get_async_session_maker  # or your database connection function

async def fix_enum():
    async_session_maker = get_async_session_maker()
    
    async with async_session_maker() as session:
        # Check current enum values
        result = await session.execute(
            text("SELECT enum_range(NULL::posttype);")
        )
        current_values = result.scalar()
        print(f"Current posttype values: {current_values}")
        
        # Add BLOG if not exists
        try:
            await session.execute(
                text("ALTER TYPE posttype ADD VALUE IF NOT EXISTS 'BLOG';")
            )
            await session.commit()
            print("✅ Successfully added 'BLOG' to posttype enum")
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
        
        # Verify
        result = await session.execute(
            text("SELECT enum_range(NULL::posttype);")
        )
        updated_values = result.scalar()
        print(f"Updated posttype values: {updated_values}")

if __name__ == "__main__":
    asyncio.run(fix_enum())