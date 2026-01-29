from app.core.cloudinary import cloudinary as cloudinary_config
import cloudinary.api

# Folders you want to wipe
CATEGORIES = [
    'reels'
]


def delete_all_media_in_folder(folder: str):
    print(f"🧹 Deleting all assets in folder: {folder}")

    next_cursor = None
    deleted_count = 0

    while True:
        result = cloudinary.api.resources(
            type="upload",
            prefix=f"{folder}/",
            max_results=100,
            next_cursor=next_cursor
        )

        resources = result.get("resources", [])
        if not resources:
            break

        public_ids = [res["public_id"] for res in resources]

        # Delete across all possible resource types
        cloudinary.api.delete_resources(public_ids, resource_type="image")
        cloudinary.api.delete_resources(public_ids, resource_type="video")
        cloudinary.api.delete_resources(public_ids, resource_type="raw")

        deleted_count += len(public_ids)
        print(f"🗑️ Deleted {len(public_ids)} assets...")

        next_cursor = result.get("next_cursor")
        if not next_cursor:
            break

    print(f"✅ Done. Total deleted from '{folder}': {deleted_count}")


def delete_all_media():
    for folder in CATEGORIES:
        delete_all_media_in_folder(folder)


if __name__ == "__main__":
    delete_all_media()
