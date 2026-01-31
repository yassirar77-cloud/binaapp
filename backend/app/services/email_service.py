"""
Email Service for BinaApp
Handles all email sending via Zoho SMTP
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from loguru import logger
from app.core.config import settings


class EmailService:
    """Email service using Zoho SMTP"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST or "smtp.zoho.com"
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.FROM_NAME
        self.support_email = settings.SUPPORT_EMAIL
        self.admin_email = settings.ADMIN_EMAIL
        self.noreply_email = settings.NOREPLY_EMAIL

    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.smtp_user and self.smtp_password)

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None
    ) -> bool:
        """
        Send an email via Zoho SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            from_email: Sender email (defaults to configured FROM_EMAIL)
            from_name: Sender name (defaults to configured FROM_NAME)
            reply_to: Reply-to email address
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            smtp_host: Override SMTP host (optional)
            smtp_port: Override SMTP port (optional)
            smtp_user: Override SMTP user (optional)
            smtp_password: Override SMTP password (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        # Use override credentials if provided, otherwise use defaults
        effective_smtp_host = smtp_host or self.smtp_host
        effective_smtp_port = smtp_port or self.smtp_port
        effective_smtp_user = smtp_user or self.smtp_user
        effective_smtp_password = smtp_password or self.smtp_password

        if not effective_smtp_user or not effective_smtp_password:
            logger.warning("Email service not configured. Skipping email send.")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{from_name or self.from_name} <{from_email or self.from_email}>"
            message["To"] = to_email

            if reply_to:
                message["Reply-To"] = reply_to
            if cc:
                message["Cc"] = ", ".join(cc)

            # Attach text content
            if text_content:
                message.attach(MIMEText(text_content, "plain"))

            # Attach HTML content
            message.attach(MIMEText(html_content, "html"))

            # Build recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email via Zoho SMTP
            # Port 465 uses SSL, Port 587 uses STARTTLS
            use_tls = effective_smtp_port == 465
            start_tls = effective_smtp_port == 587

            await aiosmtplib.send(
                message,
                hostname=effective_smtp_host,
                port=effective_smtp_port,
                username=effective_smtp_user,
                password=effective_smtp_password,
                use_tls=use_tls,
                start_tls=start_tls
            )

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    # =====================
    # Order Emails
    # =====================

    async def send_order_confirmation(
        self,
        customer_email: str,
        customer_name: str,
        order_id: str,
        order_items: List[dict],
        total_amount: float,
        delivery_address: str,
        restaurant_name: str
    ) -> bool:
        """Send order confirmation email to customer"""

        items_html = "".join([
            f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee;'>{item['name']}</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #eee; text-align: center;'>{item['quantity']}</td>"
            f"<td style='padding: 8px; border-bottom: 1px solid #eee; text-align: right;'>RM{item['price']:.2f}</td></tr>"
            for item in order_items
        ])

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10b981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .order-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .order-table th {{ background: #f3f4f6; padding: 10px; text-align: left; }}
                .total {{ font-size: 1.2em; font-weight: bold; color: #10b981; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Pesanan Disahkan!</h1>
                    <p>Terima kasih kerana memesan dengan {restaurant_name}</p>
                </div>
                <div class="content">
                    <p>Hai {customer_name},</p>
                    <p>Pesanan anda telah diterima dan sedang diproses.</p>

                    <p><strong>No. Pesanan:</strong> #{order_id}</p>

                    <table class="order-table">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: center;">Kuantiti</th>
                                <th style="text-align: right;">Harga</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>

                    <p class="total">Jumlah: RM{total_amount:.2f}</p>

                    <p><strong>Alamat Penghantaran:</strong><br>{delivery_address}</p>

                    <p>Kami akan memberitahu anda apabila pesanan anda dalam perjalanan.</p>
                </div>
                <div class="footer">
                    <p>Powered by BinaApp</p>
                    <p>Soalan? Hubungi kami di {self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=customer_email,
            subject=f"Pesanan #{order_id} Disahkan - {restaurant_name}",
            html_content=html_content,
            reply_to=self.support_email
        )

    async def send_order_status_update(
        self,
        customer_email: str,
        customer_name: str,
        order_id: str,
        status: str,
        restaurant_name: str,
        rider_name: Optional[str] = None,
        estimated_time: Optional[str] = None
    ) -> bool:
        """Send order status update email to customer"""

        status_messages = {
            "preparing": ("Pesanan Sedang Disediakan", "Restoran sedang menyediakan pesanan anda."),
            "ready": ("Pesanan Sedia untuk Diambil", "Pesanan anda sudah sedia dan menunggu rider."),
            "picked_up": ("Pesanan Dalam Perjalanan", f"Rider {rider_name or 'kami'} sedang dalam perjalanan ke lokasi anda."),
            "delivered": ("Pesanan Telah Dihantar", "Pesanan anda telah berjaya dihantar. Selamat menjamu selera!"),
            "cancelled": ("Pesanan Dibatalkan", "Pesanan anda telah dibatalkan. Sila hubungi kami jika ada pertanyaan.")
        }

        title, message = status_messages.get(status, ("Status Pesanan Dikemaskini", f"Status pesanan anda: {status}"))

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #3b82f6; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .status-badge {{ display: inline-block; padding: 8px 16px; background: #10b981; color: white; border-radius: 20px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{title}</h1>
                </div>
                <div class="content">
                    <p>Hai {customer_name},</p>

                    <p><strong>No. Pesanan:</strong> #{order_id}</p>

                    <p>{message}</p>

                    {f'<p><strong>Anggaran masa:</strong> {estimated_time}</p>' if estimated_time else ''}
                </div>
                <div class="footer">
                    <p>Pesanan dari {restaurant_name}</p>
                    <p>Powered by BinaApp</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=customer_email,
            subject=f"{title} - Pesanan #{order_id}",
            html_content=html_content
        )

    # =====================
    # Password Reset Emails
    # =====================

    async def send_password_reset(
        self,
        user_email: str,
        user_name: str,
        reset_link: str
    ) -> bool:
        """Send password reset email"""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #6366f1; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .warning {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 12px; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reset Kata Laluan</h1>
                </div>
                <div class="content">
                    <p>Hai {user_name},</p>

                    <p>Kami menerima permintaan untuk reset kata laluan akaun BinaApp anda.</p>

                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Kata Laluan</a>
                    </p>

                    <p>Atau salin pautan ini ke browser anda:</p>
                    <p style="word-break: break-all; background: #e5e7eb; padding: 10px; border-radius: 4px;">{reset_link}</p>

                    <div class="warning">
                        <strong>Nota:</strong> Pautan ini akan tamat tempoh dalam 1 jam. Jika anda tidak meminta reset kata laluan, sila abaikan emel ini.
                    </div>
                </div>
                <div class="footer">
                    <p>BinaApp - Platform Restoran Digital</p>
                    <p>Soalan? Hubungi kami di {self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=user_email,
            subject="Reset Kata Laluan BinaApp",
            html_content=html_content,
            from_email=self.noreply_email
        )

    # =====================
    # Support Emails
    # =====================

    async def send_support_inquiry(
        self,
        customer_email: str,
        customer_name: str,
        subject: str,
        message: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Send support inquiry notification to support team"""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f59e0b; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .info-box {{ background: #fff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                .message-box {{ background: #fff; border-left: 4px solid #f59e0b; padding: 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Pertanyaan Sokongan Baru</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <p><strong>Daripada:</strong> {customer_name}</p>
                        <p><strong>Emel:</strong> {customer_email}</p>
                        {f'<p><strong>User ID:</strong> {user_id}</p>' if user_id else ''}
                        <p><strong>Subjek:</strong> {subject}</p>
                    </div>

                    <p><strong>Mesej:</strong></p>
                    <div class="message-box">
                        {message}
                    </div>

                    <p>Sila balas ke emel pelanggan secepat mungkin.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=self.support_email,
            subject=f"[Sokongan] {subject}",
            html_content=html_content,
            reply_to=customer_email
        )

    # =====================
    # Admin Notification Emails
    # =====================

    async def send_admin_notification(
        self,
        subject: str,
        message: str,
        notification_type: str = "info",
        details: Optional[dict] = None
    ) -> bool:
        """Send notification email to admin"""

        type_colors = {
            "info": "#3b82f6",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444"
        }

        color = type_colors.get(notification_type, "#3b82f6")

        details_html = ""
        if details:
            details_html = "<div class='details'><h3>Butiran:</h3><ul>"
            for key, value in details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul></div>"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .details {{ background: #fff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                .details ul {{ margin: 10px 0; padding-left: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Notifikasi Admin</h1>
                    <p>{notification_type.upper()}</p>
                </div>
                <div class="content">
                    <p>{message}</p>
                    {details_html}
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=self.admin_email,
            subject=f"[BinaApp Admin] {subject}",
            html_content=html_content
        )

    async def send_new_signup_notification(
        self,
        user_email: str,
        user_name: str,
        plan: Optional[str] = None
    ) -> bool:
        """Send notification to admin when new user signs up"""

        return await self.send_admin_notification(
            subject="Pendaftaran Pengguna Baru",
            message=f"Pengguna baru telah mendaftar di BinaApp.",
            notification_type="success",
            details={
                "Nama": user_name,
                "Emel": user_email,
                "Pelan": plan or "Belum dipilih"
            }
        )

    async def send_new_subscription_notification(
        self,
        user_email: str,
        user_name: str,
        plan: str,
        amount: float
    ) -> bool:
        """Send notification to admin when user subscribes"""

        return await self.send_admin_notification(
            subject="Langganan Baru",
            message=f"Pengguna telah melanggan pelan {plan}.",
            notification_type="success",
            details={
                "Nama": user_name,
                "Emel": user_email,
                "Pelan": plan,
                "Jumlah": f"RM{amount:.2f}"
            }
        )

    # =====================
    # Subscription Reminder Emails
    # =====================

    async def send_subscription_reminder(
        self,
        user_email: str,
        user_name: str,
        days_remaining: int,
        plan_name: str,
        renewal_link: str
    ) -> bool:
        """Send subscription expiry reminder email"""

        urgency_color = "#ef4444" if days_remaining <= 3 else "#f59e0b" if days_remaining <= 7 else "#3b82f6"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {urgency_color}; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .days-box {{ text-align: center; padding: 20px; }}
                .days-number {{ font-size: 48px; font-weight: bold; color: {urgency_color}; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Langganan Hampir Tamat</h1>
                </div>
                <div class="content">
                    <p>Hai {user_name},</p>

                    <div class="days-box">
                        <p>Langganan <strong>{plan_name}</strong> anda akan tamat dalam</p>
                        <p class="days-number">{days_remaining}</p>
                        <p>hari lagi</p>
                    </div>

                    <p>Untuk terus menggunakan semua ciri BinaApp tanpa gangguan, sila perbaharui langganan anda sekarang.</p>

                    <p style="text-align: center;">
                        <a href="{renewal_link}" class="button">Perbaharui Sekarang</a>
                    </p>

                    <p>Jika anda mempunyai sebarang pertanyaan, jangan teragak-agak untuk menghubungi kami.</p>
                </div>
                <div class="footer">
                    <p>BinaApp - Platform Restoran Digital</p>
                    <p>{self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=user_email,
            subject=f"Langganan BinaApp Tamat Dalam {days_remaining} Hari",
            html_content=html_content
        )

    async def send_subscription_expired(
        self,
        user_email: str,
        user_name: str,
        plan_name: str,
        renewal_link: str
    ) -> bool:
        """Send subscription expired notification email"""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ef4444; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #10b981; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Langganan Telah Tamat</h1>
                </div>
                <div class="content">
                    <p>Hai {user_name},</p>

                    <p>Langganan <strong>{plan_name}</strong> anda telah tamat tempoh.</p>

                    <p>Beberapa ciri mungkin tidak tersedia sehingga anda memperbaharui langganan.</p>

                    <p style="text-align: center;">
                        <a href="{renewal_link}" class="button">Perbaharui Sekarang</a>
                    </p>

                    <p>Kami menghargai sokongan anda dan berharap dapat terus berkhidmat untuk anda.</p>
                </div>
                <div class="footer">
                    <p>BinaApp - Platform Restoran Digital</p>
                    <p>{self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=user_email,
            subject="Langganan BinaApp Telah Tamat",
            html_content=html_content
        )

    async def send_subscription_reactivation(
        self,
        user_email: str,
        user_name: str,
        plan_name: str,
        expiry_date: str
    ) -> bool:
        """Send subscription reactivation confirmation email"""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10b981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                .success-icon {{ font-size: 48px; text-align: center; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Langganan Berjaya Diperbaharui!</h1>
                </div>
                <div class="content">
                    <div class="success-icon">&#10004;</div>

                    <p>Hai {user_name},</p>

                    <p>Terima kasih! Langganan <strong>{plan_name}</strong> anda telah berjaya diperbaharui.</p>

                    <p><strong>Tarikh Tamat Baru:</strong> {expiry_date}</p>

                    <p>Semua ciri BinaApp kini tersedia untuk anda. Teruskan membina bisnes restoran anda!</p>
                </div>
                <div class="footer">
                    <p>BinaApp - Platform Restoran Digital</p>
                    <p>{self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self._send_email(
            to_email=user_email,
            subject="Langganan BinaApp Berjaya Diperbaharui",
            html_content=html_content
        )


# Create singleton instance
email_service = EmailService()
