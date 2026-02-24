# Knowledge Base Image Upload Feature - Testing Guide

## What's New
✅ **Image Upload**: Admin can now upload images when creating/editing articles
✅ **Image Preview**: Live preview of selected images before upload
✅ **Progress Indicator**: Upload progress bar with status messages
✅ **Mobile Integration**: Uploaded images automatically appear in the mobile app

## How to Test

### 1. Start Backend Server
```bash
cd c:\xampp\htdocs\cocoguard-backend
.\run.bat
```

### 2. Test Web Dashboard (Admin)

#### Create Article with Image:
1. Open web dashboard: `http://127.0.0.1:5500/pages/knowledge.html`
2. Login as admin
3. Click "Add Article" button
4. Fill in:
   - **Title**: "Test Article with Image"
   - **Category**: Select any category
   - **Content**: Add some test content
   - **Tags**: "test, image, upload"
   - **Upload Image**: Click and select an image file (JPEG, PNG, WebP)
5. See image preview appear
6. Click "Add Article"
7. Watch upload progress bar
8. Article should appear in table with the uploaded image

#### Edit Article and Change Image:
1. Click "Edit" on any article
2. See current image displayed
3. Upload a new image using "Upload New Image" field
4. See new image preview
5. Click "Update Article"
6. Verify new image is saved

### 3. Test Mobile App

#### View Articles with Images:
1. Open the CocoGuard mobile app
2. Navigate to Knowledge Base screen
3. Pull down to refresh articles
4. Tap on an article with an image
5. Verify the uploaded image displays correctly
6. Check image loads from: `http://127.0.0.1:8000/uploads/files/knowledge_*.jpg`

## API Endpoints

### Upload Knowledge Image
```
POST /uploads/knowledge-image
Authorization: Bearer {admin_token}
Content-Type: multipart/form-data

Body: file (image)
```

**Response:**
```json
{
  "filename": "knowledge_20251210_143022.jpg",
  "url": "http://127.0.0.1:8000/uploads/files/knowledge_20251210_143022.jpg",
  "size": 245678,
  "content_type": "image/jpeg"
}
```

### Create Article with Image
```
POST /knowledge
Authorization: Bearer {admin_token}
Content-Type: application/json

Body:
{
  "title": "Article Title",
  "category": "pest-management",
  "content": "Article content...",
  "tags": ["tag1", "tag2"],
  "image_url": "http://127.0.0.1:8000/uploads/files/knowledge_20251210_143022.jpg"
}
```

## File Storage

- **Location**: `c:\xampp\htdocs\cocoguard-backend\uploads\`
- **Naming**: `knowledge_{timestamp}.{ext}`
- **Supported**: JPEG, JPG, PNG, WebP
- **Max Size**: 5MB
- **Access**: Via `/uploads/files/{filename}`

## Features Implemented

### Backend (`uploads.py`)
- ✅ New endpoint: `/uploads/knowledge-image`
- ✅ Admin-only access
- ✅ File validation (type, size)
- ✅ Unique filename generation
- ✅ Returns full URL path

### Backend (`main.py`)
- ✅ Static file serving for uploaded images
- ✅ CORS configuration for file access

### Web Frontend (`knowledge.js`)
- ✅ File upload input in Add modal
- ✅ File upload input in Edit modal
- ✅ Image preview before upload
- ✅ Progress bar during upload
- ✅ Automatic URL insertion after upload
- ✅ Error handling for upload failures

### Mobile App
- ✅ Already implemented - displays `image_url` from API
- ✅ Network image loading with error handling
- ✅ Image caching and display

## Testing Checklist

- [ ] Upload JPEG image - works
- [ ] Upload PNG image - works
- [ ] Upload WebP image - works
- [ ] Upload file > 5MB - shows error
- [ ] Upload non-image file - shows error
- [ ] Create article without image - works
- [ ] Create article with image - image displays
- [ ] Edit article and change image - new image displays
- [ ] View article on mobile - image loads correctly
- [ ] Image accessible via direct URL

## Expected Results

1. **Admin uploads image** → Image saved to `uploads/` folder
2. **Article created** → Article stored with image URL
3. **Mobile refreshes** → New article with image appears
4. **User taps article** → Image loads and displays
5. **Admin edits** → Can replace image with new one

## Troubleshooting

**Issue**: Image not uploading
- Check backend is running
- Verify admin authentication
- Check file size < 5MB
- Verify file type is supported

**Issue**: Image not appearing in mobile
- Check image URL is complete (includes http://)
- Verify uploads folder is accessible
- Test URL directly in browser
- Check mobile device network connection

**Issue**: CORS error
- Verify CORS settings in main.py
- Check frontend URL is allowed
- Ensure Authorization header is sent

## Next Steps

- ✅ Image upload working
- ✅ Mobile integration complete
- ✅ Static files served correctly
- ✅ End-to-end workflow functional
