
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import KnowledgeArticle

# Use the correct SQLite database file (relative to backend folder)
DATABASE_URI = 'sqlite:///../cocoguard_web/cocoguard.db'
UPLOADS_DIR = '../cocoguard_web/uploads/files'

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Get all actual image filenames in uploads/files
actual_files = set(os.listdir(UPLOADS_DIR))

articles = session.query(KnowledgeArticle).all()
for article in articles:
    if article.image_url:
        # Only the filename part
        filename = os.path.basename(article.image_url)
        if filename not in actual_files:
            # Try to find a matching file by article id or title
            for f in actual_files:
                if str(article.id) in f or article.title.replace(' ', '_').lower() in f.lower():
                    print(f"Updating article {article.id}: {article.image_url} -> uploads/files/{f}")
                    article.image_url = f"uploads/files/{f}"
                    break
        else:
            # Set to correct relative path if not already
            if not article.image_url.startswith('uploads/files/'):
                print(f"Fixing path for article {article.id}: {article.image_url} -> uploads/files/{filename}")
                article.image_url = f"uploads/files/{filename}"

session.commit()
print("Image URLs updated where possible.")
