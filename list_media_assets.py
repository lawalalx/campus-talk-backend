from collections import defaultdict
from app.core.cloudinary import cloudinary as cloudinary_config
import cloudinary.api


def list_all_assets():
    """
    Lists all uploaded Cloudinary assets grouped by folder structure.
    """
    print("📂 Listing all Cloudinary assets...\n")

    assets_by_folder = defaultdict(list)
    next_cursor = None

    while True:
        result = cloudinary.api.resources(
            type="upload",
            max_results=100,
            next_cursor=next_cursor
        )

        for asset in result.get("resources", []):
            public_id = asset["public_id"]          # e.g. reels/yabatech/my_video
            resource_type = asset["resource_type"]  # image | video | raw
            url = asset.get("secure_url")

            # Split folder and filename
            if "/" in public_id:
                folder, name = public_id.rsplit("/", 1)
            else:
                folder, name = "root", public_id

            assets_by_folder[folder].append({
                "name": name,
                "type": resource_type,
                "url": url,
            })

        next_cursor = result.get("next_cursor")
        if not next_cursor:
            break

    # Pretty print
    for folder in sorted(assets_by_folder.keys()):
        print(f"📁 {folder}/")
        for asset in assets_by_folder[folder]:
            print(
                f"   ├── [{asset['type']}] {asset['name']}\n"
                f"   │    🔗 {asset['url']}"
            )
        print()

    print("✅ Done.")


if __name__ == "__main__":
    list_all_assets()
