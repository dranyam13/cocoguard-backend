# Email and SMS Configuration for CocoGuard

This file explains how to configure real email and SMS verification for the profile edit feature.

## Email Configuration (Gmail SMTP)

To enable email verification codes, you need to configure Gmail SMTP settings:

### 1. Create App Password for Gmail

1. Go to your Google Account: https://myaccount.google.com/
2. Select "Security" from the left sidebar
3. Enable "2-Step Verification" (if not already enabled)
4. Go to "App passwords" under "2-Step Verification"
5. Create a new app password for "Mail"
6. Copy the 16-character password

### 2. Update Backend Configuration

Edit `cocoguard-backend/.env` file (create if doesn't exist):

```env
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=CocoGuard
```

Replace:
- `your-email@gmail.com` with your Gmail address
- `your-app-password-here` with the 16-character app password

## SMS Configuration (Twilio)

To enable SMS verification codes, you need to set up Twilio:

### 1. Create Twilio Account

1. Sign up at https://www.twilio.com/try-twilio
2. Get a free trial account (includes $15 credit)
3. Get a phone number from Twilio console

### 2. Get Twilio Credentials

From Twilio Console (https://console.twilio.com/):
- Account SID
- Auth Token
- Your Twilio phone number

### 3. Update Backend Configuration

Add to `cocoguard-backend/.env`:

```env
# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

Replace with your actual Twilio credentials.

## Philippine SMS Providers (Alternative)

For production in the Philippines, consider local SMS providers:

### Semaphore (Philippine SMS Gateway)
- Website: https://semaphore.co/
- More affordable for Philippine numbers
- Better delivery rates for local numbers

### Globe Labs API
- Website: https://developer.globelabs.com.ph/
- For Globe subscribers

### Smart DevNet
- Website: https://devnet.smart.com.ph/
- For Smart subscribers

## Testing Without Configuration

If you don't configure email/SMS, the system will:
1. Still generate and store verification codes in the database
2. Show a warning message that SMTP/SMS is not configured
3. For testing, you can check the database directly for the code

### Check Verification Code in Database

```python
# Run in backend directory
python -c "from app.database import SessionLocal; from app.models import VerificationCode; db = SessionLocal(); codes = db.query(VerificationCode).order_by(VerificationCode.created_at.desc()).limit(5).all(); [print(f'Code: {c.code}, Email: {c.recipient}, Type: {c.type}, Expires: {c.expires_at}') for c in codes]"
```

## Restart Server After Configuration

After updating `.env` file, restart the backend server:

```bash
# Stop current server (Ctrl+C)
# Start again
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Security Notes

- Never commit `.env` file to git (already in .gitignore)
- Keep your SMTP password and Twilio tokens secure
- For production, use environment variables instead of .env file
- Codes expire after 10 minutes for security
- Codes are single-use only
