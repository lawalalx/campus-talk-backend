import os
import mimetypes
from app.core.cloudinary import cloudinary
import cloudinary.uploader

# Base folder where your media files are stored
MEDIA_BASE_FOLDER = "media_files/campus_blog"

# List of allowed categories/folders
CATEGORIES = [
    "oau",
    "unilag",
    "yabatech",
]


import re
import unicodedata
import os

def sanitize_public_id(file_path: str) -> str:
    name = os.path.splitext(os.path.basename(file_path))[0]

    # Normalize unicode (remove emojis & weird chars)
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    # Replace spaces with underscores
    name = name.strip().replace(" ", "_")

    # Remove anything not allowed
    name = re.sub(r"[^a-zA-Z0-9_\-]", "", name)

    # Prevent empty or trailing underscore
    name = name.strip("_")

    return name or "media"


def upload_file(file_path: str, folder: str):
    mime_type, _ = mimetypes.guess_type(file_path)
    extension = os.path.splitext(file_path)[1].lower()

    if mime_type and mime_type.startswith("video"):
        resource_type = "video"
    elif extension == ".svg":
        resource_type = "image"
    else:
        resource_type = "image"

    public_id = f"{folder}_{sanitize_public_id(file_path)}"


    try:
        result = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            public_id=public_id,
            resource_type=resource_type,
            overwrite=True
        )
        print(f"✅ Uploaded: {file_path} → {result.get('secure_url')}")
        return result.get("secure_url")
    except Exception as e:
        print(f"❌ Failed to upload {file_path}: {e}")
        return None





def upload_media_folder():
    """
    Walk through MEDIA_BASE_FOLDER and upload all files under valid categories.
    """
    for category in CATEGORIES:
        category_path = os.path.join(MEDIA_BASE_FOLDER, category)
        if not os.path.exists(category_path):
            print(f"⚠️ Category folder not found: {category_path}")
            continue

        for root, _, files in os.walk(category_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                upload_file(file_path, folder=category)


if __name__ == "__main__":
    upload_media_folder()
