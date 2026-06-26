"""
Seed posts for all institutions (POST, REEL, BLOG types).
At least 5 posts per institution, with Cloudinary media.

Run: cd campus-tok-app/backend && $env:PYTHONPATH="."; python seeds/seed_post.py
"""
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

# Map institution IDs to their Cloudinary media folders
INSTITUTION_FOLDERS = {
    "unilag": {
        "folder_id": "unilag",
        "images_prefix": "unilag",
        "videos_prefix": "reels/unilag",
        "school_domain": "unilag.edu.ng",
    },
    "ileife": {
        "folder_id": "ileife",
        "images_prefix": "oau",
        "videos_prefix": "reels/oau",
        "school_domain": "oauife.edu.ng",
    },
    "yabatech": {
        "folder_id": "yabatech",
        "images_prefix": "yabatech",
        "videos_prefix": "reels/yabatech",
        "school_domain": "yabatech.edu.ng",
    },
}


# ──────────────────────────────────────────────
# Rich content for each institution's posts
# ──────────────────────────────────────────────

SCHOOL_POSTS_CONTENT = {
    "unilag": [
        {
            "title": "UNILAG Hosts Largest Tech Conference in West Africa",
            "content": """UNILAG recently hosted the West Africa Tech Summit 2026, bringing together over 5,000 innovators, startup founders, and industry leaders from across the continent. The three-day event featured keynote speeches from global tech pioneers, hands-on workshops, and a hackathon that attracted over 200 student teams.

The summit highlighted UNILAG's commitment to positioning itself as Africa's leading innovation hub. The Vice-Chancellor announced a new N5 billion technology innovation fund to support student-led startups.

#TechSummit #UNILAG #InnovationHub #StudentEntrepreneurs""",
            "post_type": PostType.POST,
        },
        {
            "title": "Unilag Ogbonge Carnival 2025 Recap",
            "content": """The Unilag Ogbonge Carnival 2025 was absolutely electrifying! From the colourful cultural parade to the amazing performances by our talented students, this year's carnival was the biggest yet.

Highlights included:
🔥 The Masquerade Display that had everyone on their feet
🎵 Live performances from top Nigerian artists
💃 Dance competitions showcasing our diverse cultural heritage
🍔 Food village with delicacies from all 36 states

See you next year! #UnilagCarnival #Ogbonge #CampusLife #UnilagVibes""",
            "post_type": PostType.POST,
        },
        {
            "title": "University Life - The UNILAG Experience",
            "content": """From the moment you step through the gates of UNILAG, you know you're somewhere special. The energy, the diversity, the endless opportunities - this is more than just a university, it's a launching pad for greatness.

Whether you're studying at the iconic Senate Building, grabbing lunch at the popular Mama Cass, or networking at one of the many student events, every day at UNILAG is an adventure waiting to happen.

To all aspiring UNILAGITES, the journey is tough but the reward is worth it. 💙💛 #UnilagExperience #CampusVibes #StudentLife #UnilagProud""",
            "post_type": PostType.POST,
        },
        {
            "title": "Inside UNILAG's State-of-the-Art Research Labs",
            "content": """Take a tour of UNILAG's cutting-edge research facilities! Our institution has invested heavily in world-class laboratories across multiple disciplines.

The new Central Research Laboratory houses equipment valued at over $5 million, including advanced spectroscopy tools, electron microscopes, and molecular biology workstations.

UNILAG researchers are currently working on groundbreaking projects in renewable energy, AI-driven healthcare solutions, and sustainable agriculture that could transform the African continent.

#ResearchExcellence #UNILAG #ScienceAndInnovation #FutureOfAfrica""",
            "post_type": PostType.POST,
        },
        {
            "title": "Exploring Akoka: A Day in the Life at UNILAG",
            "content": """Ever wondered what a typical day looks like at the University of Lagos? Join us as we take you through the hustle and bustle of Africa's most dynamic campus.

From early morning lectures at the Faculty of Science to late-night study sessions at the library, from football at the Sports Centre to unwinding at the Afe Babalola Auditorium - life at UNILAG never stops.

The best part? The friendships you make and the memories you create. UNILAG is truly the place to be! 🎓✨

#DayInTheLife #UnilagStudent #CampusLife #AkokaVibes""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "Golden era of UNILAG sports: Athletes who made history",
            "content": """UNILAG has a proud tradition of producing exceptional athletes who have gone on to represent Nigeria on the global stage. From track and field stars to basketball champions, our sporting legacy is unmatched.

This year alone, UNILAG athletes won 12 gold medals at the Nigerian University Games Association (NUGA) championship, setting three new national records in the process.

The university's investment in world-class sporting facilities, including the newly renovated Sports Centre and Olympic-size swimming pool, continues to attract top athletic talent from across the country.

#UNILAGSports #NUGA #Athletes #SportsExcellence""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "Creative Showcase: UNILAG Art Exhibition 2026",
            "content": """The Department of Creative Arts at UNILAG recently held its annual art exhibition, showcasing the incredible talents of our students and faculty. The exhibition featured over 200 works spanning painting, sculpture, photography, digital art, and mixed media installations.

This year's theme, 'The African Renaissance,' challenged artists to explore themes of identity, heritage, and the continent's bright future. The standout piece was a stunning 12-foot sculpture titled 'The Rise of a New Africa' by final-year student Amara Okafor.

#CreativityUnleashed #UNILAGArts #AfricanRenaissance #StudentArtists""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "#UNILAG Campus Tour 2025 🏛️",
            "content": """Take a quick tour of the beautiful University of Lagos campus. From the iconic Senate Building to the serene Lagoon Front, discover what makes UNILAG one of Africa's most beautiful campuses! ✨🎓

#UNILAG #CampusTour #Akoka #NigeriaUniversities #StudyInNigeria""",
            "post_type": PostType.REEL,
        },
        {
            "title": "JERSEY DAY AT UNILAG 🏀🔥",
            "content": """Jersey Day at UNILAG hits different! Everyone repping their favourite teams and players. The energy on campus was unreal 🔥🔥🔥

#JerseyDay #UNILAG #CampusVibes #SportsFashion #UnilagStudents""",
            "post_type": PostType.REEL,
        },
        {
            "title": "UNILAG Cultural Day Celebration 🎭",
            "content": """Watch the vibrant Cultural Day celebration at UNILAG! Students from all tribes came together to showcase the rich diversity of Nigeria. Traditional dances, colourful attires, and lots of fun! 🕺💃🌍

#CulturalDay #UNILAG #UnityInDiversity #Nigeria #CampusLife""",
            "post_type": PostType.REEL,
        },
    ],
    "ileife": [
        {
            "title": "OAU: The Most Beautiful Campus in Africa",
            "content": """Obafemi Awolowo University, located in the ancient city of Ile-Ife, is consistently ranked as one of the most beautiful university campuses in Africa. The unique architectural design, blending modernist and traditional Yoruba elements, creates a breathtaking environment for academic pursuit.

The iconic OAU Senate Building, with its distinctive dome and sprawling green lawns, is a symbol of the university's commitment to excellence. The campus also features the famous OAU Zoo, Botanical Gardens, and the Oduduwa Hall - one of the largest auditoriums in any Nigerian university.

#OAU #BeautifulCampus #IleIfe #Architecture #AcademicExcellence""",
            "post_type": PostType.POST,
        },
        {
            "title": "Great Ife: A Legacy of Student Activism and Academic Excellence",
            "content": """Obafemi Awolowo University has a rich history of student activism that has shaped Nigeria's political landscape. From the 1970s to present day, OAU students have been at the forefront of movements for social justice and democratic reform.

The university's motto, 'For Learning and Culture,' reflects its unique position as an institution that values both academic rigour and cultural preservation. OAU's Faculty of Arts is particularly renowned for its contributions to the study of Yoruba language, literature, and African civilisations.

#GreatIfe #StudentActivism #AcademicExcellence #IfeVibes""",
            "post_type": PostType.POST,
        },
        {
            "title": "Life at Ile-Ife: The Ancient City meets Modern Academia",
            "content": """Studying at OAU means immersing yourself in the rich cultural heritage of Ile-Ife, the cradle of Yoruba civilisation. The city's ancient history blends seamlessly with modern campus life, creating a unique university experience.

Students at OAU enjoy:
🏛️ Proximity to the Ooni's Palace and other historical sites
📚 A world-class library with rare African manuscripts
🌳 A serene, green campus perfect for study and reflection
🎭 Regular cultural festivals and art exhibitions

Ife is truly where history meets the future! ✨

#IleIfe #OAU #CultureAndLearning #GreatIfeLife""",
            "post_type": PostType.POST,
        },
        {
            "title": "The Best Places to Eat in and Around OAU Campus",
            "content": """If you're a foodie at OAU, you're in luck! From the legendary 'Mama Put' spots along the Lagoon to the popular food stalls at the Student Union Building, Ile-Ife offers some of the best campus cuisine in Nigeria.

Our top picks:
🍛 Amala and Ewedu at Ife Junction - unbeatable!
🍗 Grilled fish and plantain at the Faculty of Arts
🥘 The famous OAU Fried Rice from the cafeteria
🧋 Zobo and fresh coconut from roadside vendors

Budget-friendly and delicious - that's the OAU food experience! 🍽️

#OAUFood #CampusEats #IleIfe #StudentLife #FoodReview""",
            "post_type": PostType.POST,
        },
        {
            "title": "The OAU Alumni Who Changed Nigeria",
            "content": """OAU has produced some of Nigeria's most influential figures across every sector. From Nobel Laureate Professor Wole Soyinka to literary giant Chinua Achebe (who taught here), from business moguls to political leaders - the list of distinguished OAU alumni is extraordinary.

Notable alumni include:
🌟 Professor Wole Soyinka - Nobel Laureate in Literature
🌟 Dr. Ngozi Okonjo-Iweala - WTO Director-General (attended)
🌟 Prof. Charles Soludo - Former CBN Governor
🌟 And countless captains of industry and academia

Greatness runs in the Ife blood! 💚💛

#OAUAlumni #GreatIfe #Legacy #ProudIfeite""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "Exploring the OAU Museum of Natural History",
            "content": """Did you know OAU houses one of the most extensive natural history collections in West Africa? The OAU Museum of Natural History boasts over 10,000 specimens including rare butterflies, ancient fossils, and a fascinating collection of Nigerian wildlife.

Founded in 1981, the museum serves as both a research centre and an educational resource for students and the public. Recent renovations have added interactive exhibits and a dedicated space for temporary exhibitions.

Plan your visit today! It's an eye-opening experience for anyone interested in Nigeria's natural heritage.

#OAU Museum #NaturalHistory #Education #IleIfe #Discovery""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "Inside the Minds of OAU's Award-Winning Researchers",
            "content": """OAU continues to lead the way in groundbreaking research across multiple disciplines. The university's researchers have secured competitive international grants totalling over $10 million in the past year alone.

Key research areas include drug discovery (the university's Faculty of Pharmacy is world-renowned), renewable energy solutions, and artificial intelligence applications for African development.

The university's Technology Incubation Centre has successfully spun off 15 startups in the last three years, creating hundreds of jobs for graduates.

#ResearchExcellence #OAU #Innovation #AfricanResearch""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "ODUDUWA HALL - OAU's Iconic Auditorium 🏛️",
            "content": """The magnificent Oduduwa Hall at Obafemi Awolowo University! One of the largest indoor event venues in West Africa, hosting everything from convocations to concerts. The architecture is simply breathtaking! ✨

#OAU #OduduwaHall #IleIfe #CampusArchitecture #GreatIfe""",
            "post_type": PostType.REEL,
        },
        {
            "title": "OAU Students Show Skills at Talent Hunt 2025 🎤🎶",
            "content": """Watch amazing performances from the OAU Talent Hunt 2025! From poetry to music to dance, our students are incredibly talented. The future of Nigerian entertainment is bright! 🔥

#OAU #TalentHunt #GreatIfe #StudentTalent #CampusLife""",
            "post_type": PostType.REEL,
        },
        {
            "title": "The Greenery of OAU - Nature Walk 🌿",
            "content": """Join us for a peaceful walk through OAU's lush green campus. The botanical gardens, the shady trees, and the serene environment make Ife the perfect place for both learning and relaxation. Nature at its finest! 🍃🌳

#OAU #NatureWalk #IleIfe #GreenCampus #Serenity""",
            "post_type": PostType.REEL,
        },
    ],
    "yabatech": [
        {
            "title": "75 Years of Excellence: YABATECH at the Forefront of Technical Education",
            "content": """Yaba College of Technology (YABATECH) proudly celebrates its 75-year legacy as Nigeria's first higher educational institution. Since 1947, YABATECH has been at the forefront of technical and vocational education, producing skilled professionals who have shaped Nigeria's industrial landscape.

From engineering and technology to business and applied sciences, YABATECH continues to set the standard for polytechnic education in Nigeria. The college's commitment to practical, hands-on training ensures that graduates are industry-ready from day one.

#YABATECH75 #TechnicalEducation #NigeriaFirst #PolytechnicExcellence""",
            "post_type": PostType.POST,
        },
        {
            "title": "YABATECH Innovation Hub: Where Ideas Become Reality",
            "content": """The newly launched YABATECH Innovation Hub is transforming the way students learn and create. Equipped with 3D printers, robotics labs, and a dedicated maker space, the hub provides students with the tools they need to bring their ideas to life.

The hub has already produced several award-winning innovations, including a smart irrigation system that won the national engineering competition and a mobile health diagnostic tool that's being piloted in Lagos clinics.

This is the future of technical education in Nigeria! 🚀

#InnovationHub #YABATECH #TechEducation #StudentInnovation""",
            "post_type": PostType.POST,
        },
        {
            "title": "Life at YABATECH: More Than Just Technical Training",
            "content": """Life at Yabatech is a unique blend of rigorous academic training and vibrant campus culture. From the bustling student union activities to the colourful cultural events, there's never a dull moment at Nigeria's premier polytechnic.

The college is famous for its:
🔧 Practical, hands-on approach to learning
🎵 Thriving music and arts scene
⚽ Competitive sports programmes
🤝 Strong industry partnerships for internships

YABATECH students are known for their resilience, creativity, and entrepreneurial spirit. Once a Yabatech student, always a Yabatech student! 💙💛

#LifeAtYABATECH #CampusVibes #StudentLife #TechnicalEducation""",
            "post_type": PostType.POST,
        },
        {
            "title": "The Rise of Female Engineers at YABATECH",
            "content": """YABATECH is leading the charge in promoting gender diversity in STEM fields. The college's 'Women in Engineering' programme has seen a 60% increase in female enrollment in engineering courses over the past five years.

Through mentorship programmes, scholarships, and hands-on workshops, YABATECH is creating an enabling environment for young women to thrive in traditionally male-dominated fields. The results speak for themselves - YABATECH female engineering students have won multiple national and international competitions.

The future of Nigerian engineering is female! 💪👩‍💻

#WomenInSTEM #YABATECH #FemaleEngineers #GenderEquality #STEM""",
            "post_type": PostType.POST,
        },
        {
            "title": "Behind the Scenes: YABATECH's Famous Workshop Culture",
            "content": """What sets YABATECH apart from other institutions is its famous workshop culture. Students spend countless hours in the college's well-equipped workshops, turning theoretical knowledge into practical skills.

From the mechanical engineering workshop where students build functional engines, to the electronics lab where they design circuit boards, to the fashion and design studio where creativity knows no bounds - YABATECH workshops are where magic happens.

This hands-on approach is why YABATECH graduates are some of the most sought-after professionals in the job market.

#WorkshopCulture #YABATECH #PracticalLearning #SkillAcquisition""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "YABATECH Alumni Making Waves Across the Globe",
            "content": """YABATECH alumni can be found in leadership positions across the globe, from engineering firms in the UK to tech startups in Silicon Valley. The college's emphasis on practical skills and problem-solving has produced graduates who excel wherever they go.

Some notable achievements by YABATECH alumni this year include:
🌍 Leading major infrastructure projects across Africa
💡 Patenting innovative technologies in renewable energy
🏆 Winning international design competitions
📈 Founding successful tech companies that are creating jobs

The YABATECH network is strong and growing! 🤝

#YABATECHAlumni #GlobalImpact #SuccessStories #ProudYabatechStudent""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "A New Era for Creative-Tech Education in Nigeria",
            "content": """YABATECH has partnered with leading creative-tech organisations to launch a groundbreaking programme that combines creative arts with technology. The new curriculum offers courses in game design, animation, UI/UX design, and creative coding.

This innovative programme aims to position Nigerian youth at the centre of the growing global creative economy, which is projected to be worth over $2 trillion by 2030.

Students enrolled in the programme will have access to state-of-the-art studios, industry mentors, and internship opportunities with leading creative-tech companies.

#CreativeTech #YABATECH #FutureOfWork #DigitalEconomy #Nigeria""",
            "post_type": PostType.BLOG,
        },
        {
            "title": "ILU BUN PARADE - OJUDE YABATECH 🥁🔥",
            "content": """The streets of YABATECH come alive during the Ojude Yabatech celebration! Culture, royalty, elegance - this is what makes Yabatech special. The Ilu Bun parade is a sight to behold! 🎉🪘

#YABATECH #OjudeYabatech #Culture #Parade #CampusLife""",
            "post_type": PostType.REEL,
        },
        {
            "title": "JERSEY DAY IN YABATECH 🏀🔥",
            "content": """Jersey Day at YABATECH was absolutely fire! Everyone came through with their best fits. The energy, the vibe, the community - nothing beats Yabatech on a Friday! 🔥🙌

#JerseyDay #YABATECH #CampusVibes #StreetStyle #FridayVibes""",
            "post_type": PostType.REEL,
        },
        {
            "title": "YABATECH STUDENTS SHOWCASE INVENTIONS AT TECH FAIR 🤖",
            "content": """Watch our brilliant Yabatech students showcase their amazing inventions at the annual Tech Fair! From robots to smart devices, these young innovators are solving real world problems. The future of Nigerian technology is in good hands! 🚀💡

#YABATECH #TechFair #Innovation #StudentInventors #TechNigeria""",
            "post_type": PostType.REEL,
        },
    ],
}


async def fetch_cloudinary_resources(folder_prefix: str, resource_type: str) -> list[str]:
    """Fetch media URLs from Cloudinary for a given folder prefix and resource type."""
    try:
        result = cloudinary.api.resources(
            type="upload",
            resource_type=resource_type,
            prefix=folder_prefix,
            max_results=50,
        )
        return [r["secure_url"] for r in result.get("resources", [])]
    except Exception as e:
        print(f"⚠️ Cloudinary fetch failed for {folder_prefix} ({resource_type}): {e}")
        return []


async def seed_posts():
    """Seed posts for all institutions with a mix of POST, REEL, and BLOG types."""
    async_session_maker = get_async_session_maker(force_new=True)

    async with async_session_maker() as session:
        # 1. Get all institutions
        result = await session.execute(select(Institution))
        institutions = result.scalars().all()

        if not institutions:
            print("❌ No institutions found! Run seed_data_v2.py first.")
            return

        inst_map = {inst.id: inst for inst in institutions}
        print(f"Found {len(institutions)} institutions: {list(inst_map.keys())}")

        # 2. Get the institution user for authoring posts
        #    Use danieldawodu95@gmail.com (role=INSTITUTION, linked to unilag)
        #    For other schools, we'll use the first available user
        inst_user_result = await session.execute(
            select(User).where(User.email == "danieldawodu95@gmail.com")
        )
        inst_user = inst_user_result.scalar_one_or_none()

        # Fallback: use any verified user
        if not inst_user:
            result = await session.execute(
                select(User).where(User.is_verified == True).limit(1)
            )
            inst_user = result.scalar_one_or_none()

        if not inst_user:
            print("❌ No users found to author posts!")
            return

        print(f"Using author: {inst_user.email} ({inst_user.id})")

        # 3. Fetch Cloudinary media for each institution
        cloudinary_media = {}
        for inst_id, folder_info in INSTITUTION_FOLDERS.items():
            if inst_id not in inst_map:
                continue

            images = await fetch_cloudinary_resources(
                folder_info["images_prefix"], "image"
            )
            videos = await fetch_cloudinary_resources(
                folder_info["videos_prefix"], "video"
            )

            cloudinary_media[inst_id] = {
                "images": images,
                "videos": videos,
            }
            print(f"  {inst_id}: {len(images)} images, {len(videos)} videos found")

        # 4. Create posts for each institution
        total_posts = 0
        posts_by_type = {PostType.POST: 0, PostType.REEL: 0, PostType.BLOG: 0}

        for inst_id, posts_list in SCHOOL_POSTS_CONTENT.items():
            if inst_id not in inst_map:
                print(f"⚠️ Institution '{inst_id}' not found in DB, skipping...")
                continue

            institution = inst_map[inst_id]
            media = cloudinary_media.get(inst_id, {"images": [], "videos": []})

            # Create posts with a sequential count
            for idx, post_data in enumerate(posts_list):
                post = Post(
                    author_id=inst_user.id,
                    content=post_data["content"],
                    post_type=post_data["post_type"],
                    privacy=PostPrivacy.PUBLIC,
                    school_scope=institution.id,
                )
                session.add(post)
                await session.flush()

                # Attach media based on post type
                if post_data["post_type"] == PostType.REEL:
                    # Reels get video(s)
                    video_urls = media["videos"]
                    if video_urls:
                        video_url = video_urls[idx % len(video_urls)]
                        session.add(
                            Media(
                                post_id=post.id,
                                media_type=MediaType.VIDEO,
                                url=video_url,
                                file_metadata={"seed": True},
                            )
                        )
                else:
                    # Posts and blogs get image(s)
                    image_urls = media["images"]
                    if image_urls:
                        # 1-2 images per post
                        num_images = min(2, len(image_urls))
                        for i in range(num_images):
                            img_idx = (idx * 2 + i) % len(image_urls)
                            session.add(
                                Media(
                                    post_id=post.id,
                                    media_type=MediaType.IMAGE,
                                    url=image_urls[img_idx],
                                    file_metadata={"seed": True},
                                )
                            )

                total_posts += 1
                posts_by_type[post_data["post_type"]] += 1

            print(
                f"✅ Created {len(posts_list)} posts for {institution.institution_name}"
            )

        # 5. Commit all posts
        await session.commit()
        print(
            f"\n🚀 Seeding completed! "
            f"{total_posts} posts created "
            f"(POST: {posts_by_type[PostType.POST]}, "
            f"REEL: {posts_by_type[PostType.REEL]}, "
            f"BLOG: {posts_by_type[PostType.BLOG]})"
        )


if __name__ == "__main__":
    asyncio.run(seed_posts())
