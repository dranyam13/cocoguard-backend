
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from .. import schemas, models
from ..deps import get_db, get_current_admin, get_current_user

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/{article_id}/view", response_model=dict)
def increment_article_view(article_id: int, db: Session = Depends(get_db)):
    """Increment the view count for a knowledge article (for mobile app tracking)"""
    article = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.views += 1
    db.commit()
    return {"id": article.id, "views": article.views}





class KnowledgeArticleCreate(schemas.BaseModel):
    title: str
    content: str
    category: str  # pest-management, disease-control, best-practices, etc.
    tags: Optional[List[str]] = []
    image_url: Optional[str] = None


class KnowledgeArticleUpdate(schemas.BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_published: Optional[bool] = None


class KnowledgeArticleOut(schemas.BaseModel):
    id: int
    title: str
    content: str
    category: str
    tags: List[str]
    image_url: Optional[str]
    author_id: Optional[int]
    views: int
    is_published: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[KnowledgeArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """Get published knowledge base articles (for mobile app / public)"""
    query = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.is_published == True)
    
    if category:
        query = query.filter(models.KnowledgeArticle.category == category)
    
    if tag:
        # Escape LIKE wildcards: % and _
        safe_tag = tag.replace('%', '\\%').replace('_', '\\_')
        query = query.filter(models.KnowledgeArticle.tags.like(f'%{safe_tag}%', escape='\\'))
    
    articles = query.order_by(models.KnowledgeArticle.created_at.desc()).offset(skip).limit(limit).all()
    
    # Parse tags from JSON string
    result = []
    for article in articles:
        article_dict = {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "category": article.category,
            "tags": json.loads(article.tags) if article.tags else [],
            "image_url": article.image_url,
            "author_id": article.author_id,
            "views": article.views,
            "is_published": article.is_published,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
        }
        result.append(article_dict)
    
    return result


@router.get("/all", response_model=List[KnowledgeArticleOut], dependencies=[Depends(get_current_admin)])
def list_all_articles(
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """Get ALL knowledge base articles including disabled ones (admin only)"""
    query = db.query(models.KnowledgeArticle)
    
    if category:
        query = query.filter(models.KnowledgeArticle.category == category)
    
    if tag:
        query = query.filter(models.KnowledgeArticle.tags.like(f'%{tag}%'))
    
    articles = query.order_by(models.KnowledgeArticle.created_at.desc()).offset(skip).limit(limit).all()
    
    # Parse tags from JSON string
    result = []
    for article in articles:
        article_dict = {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "category": article.category,
            "tags": json.loads(article.tags) if article.tags else [],
            "image_url": article.image_url,
            "author_id": article.author_id,
            "views": article.views,
            "is_published": article.is_published,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
        }
        result.append(article_dict)
    
    return result


@router.get("/{article_id}", response_model=KnowledgeArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a specific knowledge article"""
    article = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Increment view count
    article.views += 1
    db.commit()
    
    # Parse tags
    article_dict = {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "tags": json.loads(article.tags) if article.tags else [],
        "image_url": article.image_url,
        "author_id": article.author_id,
        "views": article.views,
        "is_published": article.is_published,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }
    return article_dict


@router.post("", response_model=KnowledgeArticleOut)
def create_article(
    article: KnowledgeArticleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
):
    """Create a new knowledge article (admin only)"""
    new_article = models.KnowledgeArticle(
        title=article.title,
        content=article.content,
        category=article.category,
        tags=json.dumps(article.tags) if article.tags else "[]",
        image_url=article.image_url,
        author_id=current_user.id,
        views=0,
        is_published=True
    )
    
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    
    # Parse tags for response
    article_dict = {
        "id": new_article.id,
        "title": new_article.title,
        "content": new_article.content,
        "category": new_article.category,
        "tags": json.loads(new_article.tags) if new_article.tags else [],
        "image_url": new_article.image_url,
        "author_id": new_article.author_id,
        "views": new_article.views,
        "is_published": new_article.is_published,
        "created_at": new_article.created_at,
        "updated_at": new_article.updated_at,
    }
    return article_dict


@router.put("/{article_id}", response_model=KnowledgeArticleOut)
def update_article(
    article_id: int,
    article_update: KnowledgeArticleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin),
):
    """Update a knowledge article (admin only)"""
    article = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Update fields if provided
    if article_update.title is not None:
        article.title = article_update.title
    if article_update.content is not None:
        article.content = article_update.content
    if article_update.category is not None:
        article.category = article_update.category
    if article_update.tags is not None:
        article.tags = json.dumps(article_update.tags)
    if article_update.image_url is not None:
        article.image_url = article_update.image_url
    if article_update.is_published is not None:
        article.is_published = article_update.is_published
    
    db.commit()
    db.refresh(article)
    
    # Parse tags for response
    article_dict = {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "tags": json.loads(article.tags) if article.tags else [],
        "image_url": article.image_url,
        "author_id": article.author_id,
        "views": article.views,
        "is_published": article.is_published,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }
    return article_dict


@router.put("/{article_id}/toggle", response_model=KnowledgeArticleOut, dependencies=[Depends(get_current_admin)])
def toggle_article(
    article_id: int,
    db: Session = Depends(get_db),
):
    """Toggle a knowledge article between published and disabled.
    Disabled articles will not appear in the mobile app."""
    article = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.is_published = not article.is_published
    db.commit()
    db.refresh(article)
    
    # Parse tags for response
    article_dict = {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "category": article.category,
        "tags": json.loads(article.tags) if article.tags else [],
        "image_url": article.image_url,
        "author_id": article.author_id,
        "views": article.views,
        "is_published": article.is_published,
        "created_at": article.created_at,
        "updated_at": article.updated_at,
    }
    return article_dict
