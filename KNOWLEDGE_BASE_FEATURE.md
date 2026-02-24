# Knowledge Base Feature

## Overview
The Knowledge Base feature allows admins to create, manage, and share educational articles about coconut farming, pest management, disease control, and best practices. Articles are accessible both through the web dashboard and the mobile application.

## Features

### Backend API (FastAPI)
- **Full CRUD Operations**: Create, Read, Update, Delete articles
- **Category Filtering**: Filter articles by category (pest-management, disease-control, best-practices, etc.)
- **Tag-based Search**: Search articles using tags
- **View Tracking**: Automatically tracks article views
- **Admin-only Operations**: Only admins can create, edit, or delete articles
- **Database Storage**: Articles stored in `knowledge_articles` table

### Web Dashboard
- **Article Management**: Add, edit, and delete articles
- **Rich Forms**: Title, category, content, tags, and image URL fields
- **Real-time Display**: Table view with ID, title, category, author, date, and views
- **Modal Forms**: Clean UI for adding and editing articles
- **API Integration**: Connected to backend API with authentication

### Mobile Application
- **Article Browsing**: View all knowledge articles
- **Category Filter**: Filter articles by category
- **Article Details**: Full article view with metadata
- **Pull to Refresh**: Refresh article list
- **Image Support**: Display article images when available
- **View Counter**: Increment view count when opening articles

## Database Schema

```sql
CREATE TABLE knowledge_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    tags TEXT,
    image_url VARCHAR(255),
    author_id INT,
    views INT DEFAULT 0,
    is_published BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
);
```

## API Endpoints

### GET /knowledge
Get all articles (with optional filtering)
- **Query Parameters**: 
  - `category` (optional): Filter by category
  - `tag` (optional): Filter by tag
  - `skip` (optional): Pagination offset
  - `limit` (optional): Results limit
- **Response**: List of articles

### GET /knowledge/{article_id}
Get a specific article
- **Path Parameter**: `article_id`
- **Response**: Article details
- **Side Effect**: Increments view count

### POST /knowledge
Create a new article (Admin only)
- **Auth Required**: Bearer token (admin role)
- **Body**:
  ```json
  {
    "title": "Article Title",
    "content": "Article content...",
    "category": "pest-management",
    "tags": ["pest", "management"],
    "image_url": "https://example.com/image.jpg"
  }
  ```
- **Response**: Created article

### PUT /knowledge/{article_id}
Update an article (Admin only)
- **Auth Required**: Bearer token (admin role)
- **Path Parameter**: `article_id`
- **Body**: Partial article update
- **Response**: Updated article

### DELETE /knowledge/{article_id}
Delete an article (Admin only)
- **Auth Required**: Bearer token (admin role)
- **Path Parameter**: `article_id`
- **Response**: Success message

## Categories

- `pest-management`: Pest Management
- `disease-control`: Disease Control
- `best-practices`: Best Practices
- `fertilization`: Fertilization
- `harvesting`: Harvesting

## Setup Instructions

### 1. Database Setup
Run the table creation script:
```bash
python add_knowledge_table.py
```

This creates the `knowledge_articles` table and inserts 5 sample articles.

### 2. Backend Setup
The backend is already configured. Ensure the server is running:
```bash
.\run.bat
```

### 3. Web Dashboard
- Navigate to the Knowledge Base page
- Login as admin
- Click "Add Article" to create new articles
- Use Edit/Delete buttons to manage existing articles

### 4. Mobile App
- The knowledge screen automatically fetches articles from the API
- Pull down to refresh the article list
- Tap any article to view full details
- Use category chips to filter articles

## Files Modified/Created

### Backend
- `app/models.py` - Added `KnowledgeArticle` model
- `app/routers/knowledge.py` - Full CRUD implementation
- `add_knowledge_table.py` - Database setup script

### Web Frontend
- `pages/knowledge.js` - Complete frontend implementation
- `pages/knowledge.html` - Table structure (minimal changes)

### Mobile App
- `lib/services/knowledge_service.dart` - API service for knowledge articles
- `lib/services/api_service.dart` - Added `getHeaders()` method
- `lib/screens/knowledge/knowledge_screen.dart` - Complete UI redesign with API integration

## Usage Examples

### Adding an Article (Web)
1. Login as admin
2. Go to Knowledge Base page
3. Click "Add Article"
4. Fill in the form:
   - Title: "How to Control Coconut Beetles"
   - Category: Pest Management
   - Content: "Detailed guide..."
   - Tags: "beetle, pest, control"
   - Image URL: (optional)
5. Click "Add Article"

### Viewing Articles (Mobile)
1. Open the app
2. Navigate to Knowledge section
3. Browse articles or filter by category
4. Tap an article to read full content
5. Pull down to refresh

## Notes

- Only admin users can create, edit, or delete articles
- All users can view published articles
- Tags are stored as JSON arrays in the database
- Views are automatically tracked when articles are opened
- The mobile app requires authentication to access articles
- Images are displayed from URLs (not uploaded to server)
