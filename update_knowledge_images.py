import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import KnowledgeArticle

# Directory containing images
IMG_DIR = r'c:\xampp\htdocs\cocoguard_web\uploads\files'

# Get all image files in the directory
image_files = [f for f in os.listdir(IMG_DIR) if f.startswith('knowledge_') and f.endswith('.jpg')]

# Map base names to full filenames
image_map = {f.split('_')[-1].replace('.jpg', ''): f for f in image_files}

def update_articles():
    db: Session = SessionLocal()
    articles = db.query(KnowledgeArticle).all()
    updated = 0
    for article in articles:
        # Try to match by pest name in image filename
        for pest_key, filename in image_map.items():
            if pest_key.lower() in article.title.lower() or pest_key.lower() in (article.content or '').lower():
                article.image_url = f'/uploads/files/{filename}'
                db.add(article)
                updated += 1
                break
    db.commit()
    db.close()
    print(f'Updated {updated} articles with image URLs.')

if __name__ == '__main__':
    update_articles()
