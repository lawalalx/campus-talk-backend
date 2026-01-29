# import asyncio
# import cloudinary
# import cloudinary.api
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select

# from app.core.config import settings
# from app.db.session import get_async_session_maker
# # Added InstitutionProfile/Institution to find the ID
# from app.db.models import Institution, Post, Media, MediaType, PostType, PostPrivacy, User, InstitutionProfile

# # Cloudinary Config
# cloudinary.config(
#     cloud_name=settings.CLOUDINARY_CLOUD_NAME,
#     api_key=settings.CLOUDINARY_API_KEY,
#     api_secret=settings.CLOUDINARY_API_SECRET,
#     secure=True
# )

# ADMIN_EMAIL = "ab@yopmail.com"

# SCHOOL_POSTS_DATA = [
#     {
#         "id": "yabatech",
#         "folder": "yabatech",
#         "content": """🎓 Celebrating Excellence: Yaba College of Technology (YABATECH) - Nigeria's First Higher Educational Institution!

# 📍 Situated in the heart of Yaba, Lagos, YABATECH holds the prestigious title of being Nigeria's first higher educational institution, established in 1947. As the country's premier technical college, we've been shaping innovators, entrepreneurs, and industry leaders for over 75 years!

# ✨ Why YABATECH?
# ✅ Pioneering Legacy: First higher institution in Nigeria (1947)
# ✅ Technical Excellence: Specialized in polytechnic education and vocational training
# ✅ Industry-Ready Graduates: Practical skills that meet market demands
# """
#     },
#     {
#         "id": "ileife", # Matches your school_scope logic
#         "folder": "oau",
#         "content": """🏛️ Discover Obafemi Awolowo University (OAU): Nigeria's Most Beautiful Campus!

# 📍 Nestled in the ancient city of Ile-Ife, Osun State, OAU stands as one of Africa's most prestigious universities, renowned for its stunning architecture, academic excellence, and rich cultural heritage since 1961.

# ✨ Why OAU?
# ✅ Architectural Marvel: Award-winning campus
# ✅ Academic Prestige: Among Africa's top universities
# ✅ Cultural Heritage: Cradle of Yoruba civilization
# ✅ Research Excellence: Leading innovations across disciplines
# """
#     },
#     {
#         "id": "unilag",
#         "folder": "unilag",
#         "content":  """🎓 Discover the University of Lagos (UNILAG): Nigeria's Premier Institution!

# 📍 Located in the vibrant heart of Akoka, Yaba, UNILAG stands as one of Nigeria's foremost universities with over 60 years of academic excellence.

# ✨ Why UNILAG?
# ✅ Academic Excellence: Top-ranked in Africa
# ✅ Innovation Hub: Research & tech leadership
# ✅ Vibrant Campus Life
# ✅ Global Alumni Network
# """
#     }
# ]






# async def fetch_cloudinary_images(folder: str) -> list[str]:
#     try:
#         result = cloudinary.api.resources(
#             type="upload",
#             resource_type="image",
#             prefix=folder,
#             max_results=20
#         )
#         return [r["secure_url"] for r in result.get("resources", [])]
#     except Exception as e:
#         print(f"⚠️ Cloudinary fetch failed for {folder}: {e}")
#         return []

# async def seed_school_posts():
#     async_session_maker = get_async_session_maker()
#     async with async_session_maker() as session:
#         # 1. Get admin user
#         result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
#         admin_user = result.scalar_one_or_none()
#         if not admin_user:
#             print(f"❌ Admin user {ADMIN_EMAIL} not found.")
#             return

#         for data in SCHOOL_POSTS_DATA:
#             # 2. Query the CORRECT model (Institution)
#             inst_result = await session.execute(
#                 select(Institution).where(Institution.id == data["id"])
#             )
#             institution = inst_result.scalar_one_or_none()
            
#             if not institution:
#                 print(f"❌ Skipping {data['id']}: Not found in Institution table.")
#                 continue

#             image_urls = await fetch_cloudinary_images(data["folder"])

#             # 3. Create 10 posts
#             for i in range(1, 11):
#                 post = Post(
#                     author_id=admin_user.id,
#                     content=f"Post #{i} for {institution.institution_name}\n\n{data['content']}",
#                     post_type=PostType.POST,
#                     privacy=PostPrivacy.PUBLIC,
#                     school_scope=institution.id, 
#                 )
#                 session.add(post)
#                 await session.flush()

#                 if image_urls:
#                     url = image_urls[(i - 1) % len(image_urls)]
#                     session.add(Media(
#                         post_id=post.id,
#                         media_type=MediaType.IMAGE,
#                         url=url,
#                         file_metadata={"seed": True}
#                     ))

#             print(f"✅ Created 10 posts for {institution.institution_name}")

#         await session.commit()
#         print("\n🚀 Seeding successful!")

# if __name__ == "__main__":
#     asyncio.run(seed_school_posts())





import asyncio
import cloudinary
import cloudinary.api
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_async_session_maker
from app.db.models import (
    Institution,
    Post,
    Media,
    MediaType,
    PostType,
    PostPrivacy,
    User,
)

# -------------------------
# Cloudinary config
# -------------------------
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

ADMIN_EMAIL = "ab@yopmail.com"



SCHOOL_BLOG_DATA = [
    {
        "id": "yabatech",
        "folder": "yabatech",
        "content": """🎓 Celebrating Excellence: Yaba College of Technology (YABATECH)

Established in 1947, Yaba College of Technology (YABATECH) holds the distinguished honour of being Nigeria’s first higher educational institution. Located in the heart of Yaba, Lagos, the institution has played a foundational role in shaping Nigeria’s technical and professional education landscape for over seven decades.

YABATECH is widely recognised for its strong focus on practical, hands-on training across disciplines such as engineering, technology, applied sciences, management, art, and vocational studies. The institution offers National Diploma (ND), Higher National Diploma (HND), and postgraduate diploma programmes designed to equip students with industry-ready skills.

Beyond academics, YABATECH is known for pioneering initiatives such as its Centre for Entrepreneurship Development, which empowers students to translate technical knowledge into viable businesses. With campuses in Yaba and Epe, and a legacy of producing innovators, technicians, and industry leaders, YABATECH remains a cornerstone of Nigeria’s educational and industrial development."""
    },
    {
        "id": "ileife",
        "folder": "oau",
        "content": """🏛️ Discover Obafemi Awolowo University (OAU): The Citadel of Wisdom

Obafemi Awolowo University (OAU), located in the historic city of Ile-Ife, Osun State, is one of Nigeria’s most prestigious and intellectually vibrant universities. Founded in 1961 as the University of Ife, the institution was later renamed in honour of Chief Obafemi Awolowo, a renowned nationalist and advocate of education-driven development.

OAU is celebrated for its iconic campus architecture, often described as one of the most beautiful university campuses in Africa. The university began with five faculties and has since expanded into a comprehensive academic institution offering programmes across sciences, humanities, social sciences, engineering, health sciences, and technology.

With a strong culture of research, critical thinking, and social responsibility, OAU has produced generations of scholars, leaders, and professionals who have made significant contributions within Nigeria and globally. Its enduring commitment to academic excellence and cultural heritage continues to define its identity as the true Citadel of Wisdom."""
    },
    {
        "id": "unilag",
        "folder": "unilag",
        "content": """🎓 Discover the University of Lagos (UNILAG): A Legacy of Excellence

The University of Lagos (UNILAG) was established in 1962 as one of Nigeria’s first generation universities, with a mandate to provide high-quality education and advance research for national development. Situated in Akoka, Lagos, the university occupies a strategic location within Nigeria’s commercial and innovation hub.

UNILAG has grown into a multi-campus institution offering a wide range of academic programmes across medicine, engineering, law, arts, sciences, education, and management sciences. Over the years, it has built a strong reputation for academic rigour, research output, and a vibrant student community.

Known for producing influential alumni across public service, business, academia, and the creative industries, UNILAG continues to uphold its mission of excellence in teaching, learning, and service. With a forward-looking vision and a dynamic campus culture, the University of Lagos remains a leading force in shaping Nigeria’s future."""
    },
]


async def fetch_cloudinary_images(folder: str) -> list[str]:
    try:
        result = cloudinary.api.resources(
            type="upload",
            resource_type="image",
            prefix=folder,
            max_results=30,
        )
        return [r["secure_url"] for r in result.get("resources", [])]
    except Exception as e:
        print(f"⚠️ Cloudinary fetch failed for {folder}: {e}")
        return []


async def seed_school_blogs():
    async_session_maker = get_async_session_maker()

    async with async_session_maker() as session:
        # 1. Fetch admin user
        result = await session.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ Admin user not found")
            return

        for school in SCHOOL_BLOG_DATA:
            # 2. Fetch institution
            inst_result = await session.execute(
                select(Institution).where(Institution.id == school["id"])
            )
            institution = inst_result.scalar_one_or_none()

            if not institution:
                print(f"❌ Institution {school['id']} not found")
                continue

            image_urls = await fetch_cloudinary_images(school["folder"])

            if not image_urls:
                print(f"⚠️ No images found for {school['id']}")

            # 3. Create BLOG posts
            for i in range(1, 6):
                post = Post(
                    author_id=admin.id,
                    content=f"{school['content']}\n\nBlog #{i}",
                    post_type=PostType.BLOG,
                    privacy=PostPrivacy.PUBLIC,
                    school_scope=institution.id,
                )
                session.add(post)
                await session.flush()

                # Attach 1–3 images per blog
                for url in image_urls[i % max(len(image_urls), 1):][:3]:
                    session.add(
                        Media(
                            post_id=post.id,
                            media_type=MediaType.IMAGE,
                            url=url,
                            file_metadata={"seed": True},
                        )
                    )

            print(f"✅ Seeded blogs for {institution.institution_name}")

        await session.commit()
        print("\n🚀 BLOG seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_school_blogs())
