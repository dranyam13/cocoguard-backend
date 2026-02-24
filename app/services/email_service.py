import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_verification_email(to_email: str, code: str, subject: str = None, template_type: str = "verification") -> bool:
    """Send verification code via email
    
    Args:
        to_email: Recipient email address
        code: 6-digit verification code
        subject: Custom email subject (optional)
        template_type: Type of email template - 'verification', '2fa_setup', '2fa_login'
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        
        # Set subject based on template type
        if subject:
            message["Subject"] = subject
        elif template_type == "2fa_setup":
            message["Subject"] = "CocoGuard - Enable Two-Factor Authentication"
        elif template_type == "2fa_login":
            message["Subject"] = "CocoGuard - Login Verification Code"
        else:
            message["Subject"] = "CocoGuard - Email Verification Code"
            
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = to_email

        # Create HTML content based on template type
        if template_type == "2fa_setup":
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden;">
                        <div style="background: linear-gradient(135deg, #16a34a, #15803d); padding: 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🔐 Enable 2FA</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Two-Factor Authentication Setup</p>
                        </div>
                        <div style="padding: 30px;">
                            <p style="color: #374151; font-size: 16px;">You're enabling Two-Factor Authentication for extra security on your CocoGuard account.</p>
                            <p style="color: #374151; font-size: 16px;">Enter this verification code to complete setup:</p>
                            <div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); padding: 25px; text-align: center; font-size: 36px; font-weight: bold; letter-spacing: 10px; margin: 25px 0; border-radius: 12px; color: #166534; border: 2px solid #bbf7d0;">
                                {code}
                            </div>
                            <p style="color: #6b7280; font-size: 14px; text-align: center;">⏱️ This code expires in <strong>10 minutes</strong></p>
                            <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #f59e0b;">
                                <p style="color: #92400e; margin: 0; font-size: 14px;">⚠️ If you didn't request this, please ignore this email and secure your account.</p>
                            </div>
                        </div>
                        <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="color: #6b7280; font-size: 12px; margin: 0;">🥥 CocoGuard - Coconut Pest Detection System</p>
                        </div>
                    </div>
                </body>
            </html>
            """
        elif template_type == "2fa_login":
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden;">
                        <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 30px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🔑 Login Verification</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Complete your sign-in</p>
                        </div>
                        <div style="padding: 30px;">
                            <p style="color: #374151; font-size: 16px;">Someone is trying to sign in to your CocoGuard account.</p>
                            <p style="color: #374151; font-size: 16px;">If this is you, enter this verification code:</p>
                            <div style="background: linear-gradient(135deg, #eff6ff, #dbeafe); padding: 25px; text-align: center; font-size: 36px; font-weight: bold; letter-spacing: 10px; margin: 25px 0; border-radius: 12px; color: #1d4ed8; border: 2px solid #93c5fd;">
                                {code}
                            </div>
                            <p style="color: #6b7280; font-size: 14px; text-align: center;">⏱️ This code expires in <strong>10 minutes</strong></p>
                            <div style="background-color: #fef2f2; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #ef4444;">
                                <p style="color: #991b1b; margin: 0; font-size: 14px;">🚨 If you didn't try to log in, someone may be trying to access your account. Please change your password immediately.</p>
                            </div>
                        </div>
                        <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="color: #6b7280; font-size: 12px; margin: 0;">🥥 CocoGuard - Coconut Pest Detection System</p>
                        </div>
                    </div>
                </body>
            </html>
            """
        else:
            # Default verification email
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #2d7a3e;">CocoGuard Email Verification</h2>
                        <p>Your verification code is:</p>
                        <div style="background-color: #f0f0f0; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">
                            {code}
                        </div>
                        <p>This code will expire in 10 minutes.</p>
                        <p>If you didn't request this code, please ignore this email.</p>
                        <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
                        <p style="color: #666; font-size: 12px;">CocoGuard - Coconut Pest Detection System</p>
                    </div>
                </body>
            </html>
            """

        # Attach HTML content
        message.attach(MIMEText(html, "html"))

        # Send email
        if not settings.smtp_username or not settings.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email send")
            return False

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_username,
            password=settings.smtp_password,
        )

        logger.info(f"Verification email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        return False


async def send_password_reset_email(to_email: str, code: str, username: str = "") -> bool:
    """Send password reset code via email"""
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "CocoGuard - Password Reset Code"
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = to_email

        greeting = f"Hi {username}," if username else "Hello,"

        # Create HTML content
        html = f"""
        <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 0; margin: 0; background-color: #f4f4f4;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #16a34a, #15803d); padding: 30px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 28px;">🥥 CocoGuard</h1>
                        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 14px;">Password Reset Request</p>
                    </div>
                    
                    <!-- Body -->
                    <div style="padding: 40px 30px;">
                        <p style="color: #333; font-size: 16px; margin: 0 0 20px 0;">{greeting}</p>
                        
                        <p style="color: #555; font-size: 15px; line-height: 1.6;">
                            We received a request to reset your password for your CocoGuard account. 
                            Use the verification code below to complete the process:
                        </p>
                        
                        <!-- Code Box -->
                        <div style="background: linear-gradient(135deg, #e8f5e9, #c8e6c9); padding: 25px; text-align: center; border-radius: 12px; margin: 30px 0; border: 2px dashed #16a34a;">
                            <p style="color: #666; font-size: 12px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 2px;">Your Verification Code</p>
                            <div style="font-size: 36px; font-weight: bold; color: #16a34a; letter-spacing: 12px; font-family: 'Courier New', monospace;">
                                {code}
                            </div>
                        </div>
                        
                        <!-- Warning -->
                        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                            <p style="color: #856404; font-size: 14px; margin: 0;">
                                ⏰ <strong>This code will expire in 15 minutes.</strong>
                            </p>
                        </div>
                        
                        <p style="color: #555; font-size: 14px; line-height: 1.6;">
                            If you didn't request this password reset, please ignore this email or contact our support team 
                            if you have concerns about your account security.
                        </p>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                        <p style="color: #666; font-size: 12px; margin: 0; text-align: center;">
                            This is an automated message from CocoGuard - Coconut Pest Detection System.<br>
                            Please do not reply to this email.
                        </p>
                        <p style="color: #999; font-size: 11px; margin: 15px 0 0 0; text-align: center;">
                            © 2026 CocoGuard. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        # Plain text alternative
        plain_text = f"""
{greeting}

We received a request to reset your password for your CocoGuard account.

Your Verification Code: {code}

This code will expire in 15 minutes.

If you didn't request this password reset, please ignore this email.

--
CocoGuard - Coconut Pest Detection System
        """

        # Attach both plain text and HTML
        message.attach(MIMEText(plain_text, "plain"))
        message.attach(MIMEText(html, "html"))

        # Send email
        if not settings.smtp_username or not settings.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email send")
            # For development: return True with logged code
            logger.info(f"[DEV MODE] Password reset code for {to_email}: {code}")
            return True

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_username,
            password=settings.smtp_password,
        )

        logger.info(f"Password reset email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return False
