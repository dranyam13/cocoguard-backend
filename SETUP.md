# CocoGuard Backend Setup Guide

## Quick Start

### 1. Prerequisites
- Python 3.9+
- pip (Python package manager)
- Virtual Environment (venv)

### 2. Installation

#### Step 1: Navigate to backend directory
```bash
cd c:\xampp\htdocs\cocoguard-backend
```

#### Step 2: Create virtual environment
```bash
python -m venv venv
```

#### Step 3: Activate virtual environment
```bash
# On Windows
venv\Scripts\activate

# On Mac/Linux
source venv/bin/activate
```

#### Step 4: Install dependencies
```bash
pip install -r requirements.txt
```

#### Step 5: Setup environment variables
```bash
# Copy the example file
copy .env.example .env

# Edit .env with your settings (optional - defaults are provided)
# Important: Change SECRET_KEY in production!
```

### 3. Running the Backend

```bash
# Make sure you're in the backend directory with venv activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

API Documentation (Swagger UI): **http://localhost:8000/docs**

## API Endpoints Overview

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user

### Users
- `GET /users/me` - Get current user profile
- `GET /users` - List all users (admin only)

### Farms
- `GET /farms` - List user's farms
- `POST /farms` - Create new farm
- `GET /farms/{id}` - Get farm details
- `PUT /farms/{id}` - Update farm
- `DELETE /farms/{id}` - Delete farm

### Pest Types
- `GET /pest-types` - List all pest types
- `GET /pest-types/{id}` - Get pest type details
- `POST /pest-types` - Create pest type (admin only)
- `PUT /pest-types/{id}` - Update pest type (admin only)

### Scans
- `POST /scans` - Create new scan
- `GET /scans/my-scans` - List user's scans
- `GET /scans/{id}` - Get scan details
- `PUT /scans/{id}/status` - Update scan status (admin only)

### File Uploads
- `POST /uploads/scan-image` - Upload scan image
- `GET /uploads/files/{filename}` - Get uploaded file
- `DELETE /uploads/files/{filename}` - Delete file

### Feedback
- `POST /feedback` - Submit feedback
- `GET /feedback` - List all feedback (admin only)
- `GET /feedback/user/me` - Get user's feedback

### Knowledge Base
- `GET /knowledge` - List articles
- `GET /knowledge/{id}` - Get article
- `GET /knowledge/category/{category}` - Get articles by category
- `POST /knowledge` - Create article (admin only)

### Analytics
- `GET /analytics/dashboard/summary` - Dashboard summary
- `GET /analytics/scans/by-pest` - Scans by pest type
- `GET /analytics/scans/by-status` - Scans by status
- `GET /analytics/scans/trends` - Daily scan trends
- `GET /analytics/farms/summary` - Farm summaries
- `GET /analytics/admin/system-stats` - System stats (admin only)

## Database

The backend uses SQLite by default for development. To switch to MySQL:

1. Update `.env` file:
   ```
   DATABASE_URL=mysql+pymysql://user:password@localhost/cocoguard_db
   ```

2. Install MySQL driver:
   ```bash
   pip install pymysql
   ```

## Testing the API

### Option 1: Using Swagger UI
Open http://localhost:8000/docs in your browser

### Option 2: Using curl
```bash
# Register
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"John Doe","username":"johndoe","email":"john@example.com","password":"password123"}'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email_or_username":"john@example.com","password":"password123"}'

# Get current user (use token from login response)
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Connecting the Web Frontend

1. The web frontend already includes `api-client.js` for API communication
2. Update the API base URL in browser localStorage if needed:
   ```javascript
   localStorage.setItem('api_base_url', 'http://localhost:8000');
   ```
3. The login system will automatically use the API for authentication

## Connecting the Flutter Mobile App

In your Flutter app, configure the API base URL:

```dart
const String API_BASE_URL = 'http://10.0.2.2:8000'; // For Android emulator
// or 'http://localhost:8000' for web testing
```

Use HTTP client to make requests:
```dart
final response = await http.post(
  Uri.parse('$API_BASE_URL/auth/login'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'email_or_username': email,
    'password': password,
  }),
);
```

## Production Deployment

### Important Security Steps:
1. **Change SECRET_KEY** - Generate a strong random key
2. **Set ALLOWED_ORIGINS** - Restrict CORS to your domains only
3. **Use environment variables** - Load sensitive config from .env
4. **Enable HTTPS** - Use SSL certificate
5. **Use a production database** - MySQL or PostgreSQL instead of SQLite
6. **Use a production server** - Deploy with Gunicorn/uWSGI
7. **Setup backups** - Regular database backups

### Example Production Deployment (using Gunicorn):
```bash
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Troubleshooting

### Port already in use
```bash
# Change the port
uvicorn app.main:app --reload --port 8001
```

### Module import errors
```bash
python restart_server.py
```

### Database errors
Delete `cocoguard.db` to reset the database:
```bash
rm cocoguard.db
```

## Support

For issues or questions, check:
1. API documentation: http://localhost:8000/docs
2. Backend code in `app/` folder
3. Error messages in console output

Happy coding! 🥥
