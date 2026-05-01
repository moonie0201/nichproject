import os
import glob
import re
from datetime import datetime

# Hugo blog content directory
BLOG_DIR = "web/content/ko/blog"


def parse_markdown(filepath):
    """Parses markdown file to extract frontmatter and body."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple regex for frontmatter (--- YAML ---)
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        body = match.group(2)
        return frontmatter, body
    return None, content


def get_recent_posts(limit=3):
    """Lists recent blog posts."""
    posts = []
    for file in glob.glob(os.path.join(BLOG_DIR, "*.md")):
        posts.append(
            {
                "path": file,
                "filename": os.path.basename(file),
                "mtime": os.path.getmtime(file),
            }
        )

    # Sort by modification time, newest first
    posts.sort(key=lambda x: x["mtime"], reverse=True)
    return posts[:limit]


if __name__ == "__main__":
    recent = get_recent_posts()
    print(f"Recent posts in {BLOG_DIR}:")
    for post in recent:
        frontmatter, body = parse_markdown(post["path"])
        print(f"\n--- {post['filename']} ---")
        print(
            f"Frontmatter excerpt: {frontmatter[:100] if frontmatter else 'No frontmatter'}..."
        )
        print(f"Body length: {len(body)}")
