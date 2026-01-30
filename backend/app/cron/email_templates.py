"""
Email Templates for Subscription Notifications
All templates in Malay (Bahasa Malaysia) for Malaysian market

Templates:
- REMINDER_5_DAYS: 5 days before subscription expires
- REMINDER_3_DAYS: 3 days before subscription expires
- EXPIRED_NOTICE: When subscription has expired, entering grace
- GRACE_STARTED: Grace period has started
- LOCK_WARNING: Final warning before lock (same day)
- LOCKED_NOTICE: Account has been locked
- UNLOCKED_NOTICE: Account has been unlocked after payment
"""

from typing import Dict, Any


def get_base_styles() -> str:
    """Return base CSS styles for email templates"""
    return """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { padding: 30px 20px; text-align: center; border-radius: 12px 12px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        .content { background: #ffffff; padding: 30px; border-radius: 0 0 12px 12px; }
        .button { display: inline-block; padding: 14px 28px; background: #10b981; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }
        .button:hover { background: #059669; }
        .warning-box { background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .danger-box { background: #fee2e2; border: 1px solid #ef4444; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .info-box { background: #e0f2fe; border: 1px solid #0ea5e9; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .success-box { background: #dcfce7; border: 1px solid #22c55e; padding: 15px; border-radius: 8px; margin: 20px 0; }
        .days-box { text-align: center; padding: 20px; background: #f3f4f6; border-radius: 8px; margin: 20px 0; }
        .days-number { font-size: 48px; font-weight: bold; margin: 10px 0; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 0.85em; padding: 20px; }
        .footer p { margin: 5px 0; }
        .divider { height: 1px; background: #e5e7eb; margin: 20px 0; }
        ul { padding-left: 20px; }
        li { margin: 8px 0; }
    </style>
    """


def render_reminder_5_days(
    name: str,
    end_date: str,
    plan_name: str,
    price: float,
    payment_url: str,
    support_email: str = "support@binaapp.com"
) -> Dict[str, str]:
    """
    5 days before subscription expires reminder email

    Returns:
        Dict with 'subject', 'html', 'text' keys
    """
    subject = "Langganan BinaApp anda akan tamat dalam 5 hari"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white;">
                <h1>Peringatan Langganan</h1>
                <p>Langganan anda akan tamat tidak lama lagi</p>
            </div>
            <div class="content">
                <p>Assalamualaikum {name},</p>

                <div class="days-box">
                    <p>Langganan BinaApp anda akan tamat dalam</p>
                    <p class="days-number" style="color: #f59e0b;">5</p>
                    <p>hari lagi</p>
                </div>

                <div class="warning-box">
                    <strong>Tarikh Tamat:</strong> {end_date}<br>
                    <strong>Pakej Semasa:</strong> {plan_name} - RM{price:.2f}/bulan
                </div>

                <p>Untuk mengelakkan gangguan perkhidmatan, sila perbaharui langganan anda sebelum tarikh tamat.</p>

                <p style="text-align: center;">
                    <a href="{payment_url}" class="button">Bayar Sekarang</a>
                </p>

                <div class="divider"></div>

                <p style="font-size: 0.9em; color: #666;">
                    <strong>Nota:</strong> Akaun dan data anda tidak akan dipadam.
                    Ia akan diaktifkan semula secara automatik selepas pembayaran dibuat.
                </p>
            </div>
            <div class="footer">
                <p>BinaApp - Platform Restoran Digital</p>
                <p>Soalan? Hubungi kami di {support_email}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
Assalamualaikum {name},

Langganan BinaApp anda akan tamat dalam 5 hari.

Tarikh Tamat: {end_date}
Pakej Semasa: {plan_name} - RM{price:.2f}/bulan

Sila bayar sekarang untuk elak gangguan perkhidmatan:
{payment_url}

---
Akaun dan data anda tidak akan dipadam. Ia akan diaktifkan semula selepas pembayaran dibuat.

BinaApp - Platform Restoran Digital
Soalan? Hubungi kami di {support_email}
    """

    return {"subject": subject, "html": html, "text": text}


def render_reminder_3_days(
    name: str,
    end_date: str,
    plan_name: str,
    price: float,
    payment_url: str,
    support_email: str = "support@binaapp.com"
) -> Dict[str, str]:
    """3 days before subscription expires reminder email"""
    subject = "Langganan BinaApp anda akan tamat dalam 3 hari"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white;">
                <h1>Peringatan Segera!</h1>
                <p>Langganan anda akan tamat tidak lama lagi</p>
            </div>
            <div class="content">
                <p>Assalamualaikum {name},</p>

                <div class="days-box" style="background: #fee2e2;">
                    <p>Langganan BinaApp anda akan tamat dalam</p>
                    <p class="days-number" style="color: #ef4444;">3</p>
                    <p>hari lagi</p>
                </div>

                <div class="danger-box">
                    <strong>Tarikh Tamat:</strong> {end_date}<br>
                    <strong>Pakej:</strong> {plan_name} - RM{price:.2f}/bulan
                </div>

                <p><strong>Bertindak segera</strong> untuk mengelakkan website anda dilocked!</p>

                <p style="text-align: center;">
                    <a href="{payment_url}" class="button" style="background: #ef4444;">Bayar Sekarang</a>
                </p>

                <div class="divider"></div>

                <p style="font-size: 0.9em; color: #666;">
                    <strong>Nota:</strong> Akaun dan data anda tidak akan dipadam.
                </p>
            </div>
            <div class="footer">
                <p>BinaApp - Platform Restoran Digital</p>
                <p>Soalan? Hubungi kami di {support_email}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
Assalamualaikum {name},

PERINGATAN SEGERA!

Langganan BinaApp anda akan tamat dalam 3 hari.

Tarikh Tamat: {end_date}
Pakej: {plan_name} - RM{price:.2f}/bulan

Bertindak segera untuk mengelakkan website anda dilocked!
{payment_url}

---
Akaun dan data anda tidak akan dipadam.

BinaApp - Platform Restoran Digital
    """

    return {"subject": subject, "html": html, "text": text}


def render_expired_notice(
    name: str,
    plan_name: str,
    grace_end_date: str,
    payment_url: str,
    support_email: str = "support@binaapp.com"
) -> Dict[str, str]:
    """Subscription has expired, entering grace period"""
    subject = "Langganan BinaApp anda telah tamat"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); color: white;">
                <h1>Langganan Telah Tamat</h1>
            </div>
            <div class="content">
                <p>Assalamualaikum {name},</p>

                <p>Langganan <strong>{plan_name}</strong> anda telah tamat.</p>

                <div class="danger-box">
                    <strong>Anda mempunyai 5 hari lagi sebelum website dilocked.</strong>
                    <br><br>
                    Tarikh Lock: {grace_end_date}
                </div>

                <p>Selepas dilocked:</p>
                <ul>
                    <li>Dashboard tidak boleh diakses</li>
                    <li>Website tidak aktif untuk pelanggan</li>
                    <li>Pesanan tidak boleh diterima</li>
                </ul>

                <p style="text-align: center;">
                    <a href="{payment_url}" class="button" style="background: #ef4444;">Bayar Sekarang</a>
                </p>

                <div class="divider"></div>

                <p style="font-size: 0.9em; color: #666;">
                    <strong>Nota:</strong> Akaun dan data anda tidak akan dipadam.
                    Ia akan diaktifkan semula secara automatik selepas pembayaran dibuat.
                </p>
            </div>
            <div class="footer">
                <p>BinaApp - Platform Restoran Digital</p>
                <p>Soalan? Hubungi kami di {support_email}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
Assalamualaikum {name},

Langganan {plan_name} anda telah tamat.

Anda mempunyai 5 hari lagi sebelum website dilocked.
Tarikh Lock: {grace_end_date}

Selepas dilocked:
- Dashboard tidak boleh diakses
- Website tidak aktif untuk pelanggan
- Pesanan tidak boleh diterima

Bayar sekarang: {payment_url}

---
Akaun dan data anda tidak akan dipadam. Ia akan diaktifkan semula selepas pembayaran dibuat.

BinaApp - Platform Restoran Digital
    """

    return {"subject": subject, "html": html, "text": text}


def render_lock_warning(
    name: str,
    payment_url: str,
    support_email: str = "support@binaapp.com"
) -> Dict[str, str]:
    """Final warning - account will be locked today"""
    subject = "Website anda akan dilocked hari ini!"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #991b1b 0%, #7f1d1d 100%); color: white;">
                <h1>NOTIS TERAKHIR</h1>
                <p>Website akan dilocked hari ini!</p>
            </div>
            <div class="content">
                <p>Assalamualaikum {name},</p>

                <div class="danger-box" style="border-width: 2px;">
                    <p style="font-size: 1.1em; margin: 0;"><strong>Ini adalah notis terakhir. Website BinaApp anda akan dilocked HARI INI.</strong></p>
                </div>

                <p><strong>Selepas dikunci:</strong></p>
                <ul>
                    <li>Dashboard tidak boleh diakses</li>
                    <li>Website tidak aktif untuk pelanggan</li>
                    <li>Pesanan tidak boleh diterima</li>
                </ul>

                <p style="text-align: center;">
                    <a href="{payment_url}" class="button" style="background: #991b1b; font-size: 1.1em; padding: 16px 32px;">
                        BAYAR SEKARANG - Aktifkan Semula Serta-merta
                    </a>
                </p>

                <div class="divider"></div>

                <div class="info-box">
                    <strong>Nota Penting:</strong><br>
                    Akaun dan data anda <strong>TIDAK</strong> akan dipadam.
                    Ia akan diaktifkan semula secara automatik selepas pembayaran dibuat.
                </div>
            </div>
            <div class="footer">
                <p>BinaApp - Platform Restoran Digital</p>
                <p>Soalan? Hubungi kami di {support_email}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
Assalamualaikum {name},

NOTIS TERAKHIR!

Ini adalah notis terakhir. Website BinaApp anda akan dilocked HARI INI.

Selepas dikunci:
- Dashboard tidak boleh diakses
- Website tidak aktif untuk pelanggan
- Pesanan tidak boleh diterima

Bayar sekarang untuk aktifkan semula serta-merta:
{payment_url}

---
Akaun dan data anda TIDAK akan dipadam. Ia akan diaktifkan semula selepas pembayaran dibuat.

BinaApp - Platform Restoran Digital
    """

    return {"subject": subject, "html": html, "text": text}


def render_locked_notice(
    name: str,
    lock_reason: str,
    payment_url: str,
    support_email: str = "support@binaapp.com"
) -> Dict[str, str]:
    """Account has been locked"""
    subject = "Akaun BinaApp anda telah dikunci"

    reason_text = {
        "subscription_expired": "langganan tamat tempoh",
        "payment_failed": "pembayaran gagal",
        "subscription_locked": "langganan tidak aktif"
    }.get(lock_reason, "langganan tidak aktif")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #374151 0%, #1f2937 100%); color: white;">
                <h1>Akaun Dikunci</h1>
            </div>
            <div class="content">
                <p>Assalamualaikum {name},</p>

                <p>Akaun BinaApp anda telah dikunci kerana {reason_text}.</p>

                <div class="danger-box">
                    <p style="margin: 0;"><strong>Status semasa:</strong></p>
                    <ul style="margin: 10px 0 0 0;">
                        <li>Dashboard: <span style="color: #ef4444;">Tidak boleh diakses</span></li>
                        <li>Website: <span style="color: #ef4444;">Tidak aktif</span></li>
                        <li>Pesanan: <span style="color: #ef4444;">Tidak boleh diterima</span></li>
                    </ul>
                </div>

                <p><strong>Untuk mengaktifkan semula akaun anda:</strong></p>
                <ol>
                    <li>Klik butang di bawah</li>
                    <li>Buat pembayaran</li>
                    <li>Akaun anda akan aktif semula secara automatik!</li>
                </ol>

                <p style="text-align: center;">
                    <a href="{payment_url}" class="button" style="background: #10b981;">
                        Aktifkan Semula Akaun
                    </a>
                </p>

                <div class="divider"></div>

                <div class="success-box">
                    <strong>Berita Baik!</strong><br>
                    Semua data anda masih selamat. Akaun anda akan kembali aktif
                    sebaik sahaja pembayaran berjaya.
                </div>
            </div>
            <div class="footer">
                <p>BinaApp - Platform Restoran Digital</p>
                <p>Perlukan bantuan? Hubungi kami di {support_email}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
Assalamualaikum {name},

Akaun BinaApp anda telah dikunci kerana {reason_text}.

Status semasa:
- Dashboard: Tidak boleh diakses
- Website: Tidak aktif
- Pesanan: Tidak boleh diterima

Untuk mengaktifkan semula:
1. Klik pautan di bawah
2. Buat pembayaran
3. Akaun anda akan aktif semula secara automatik!

Aktifkan semula: {payment_url}

---
Semua data anda masih selamat. Akaun anda akan kembali aktif sebaik sahaja pembayaran berjaya.

BinaApp - Platform Restoran Digital
    """

    return {"subject": subject, "html": html, "text": text}


def render_unlocked_notice(
    name: str,
    plan_name: str,
    new_end_date: str,
    dashboard_url: str,
    support_email: str = "support@binaapp.com"
) -> Dict[str, str]:
    """Account has been unlocked after payment"""
    subject = "Akaun BinaApp anda telah diaktifkan semula!"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white;">
                <h1>Akaun Aktif Semula!</h1>
                <p>Terima kasih atas pembayaran anda</p>
            </div>
            <div class="content">
                <p>Assalamualaikum {name},</p>

                <div class="success-box">
                    <p style="font-size: 1.2em; margin: 0; text-align: center;">
                        <strong>Akaun anda telah berjaya diaktifkan semula!</strong>
                    </p>
                </div>

                <p><strong>Butiran Langganan:</strong></p>
                <ul>
                    <li><strong>Pakej:</strong> {plan_name}</li>
                    <li><strong>Tarikh Tamat Baru:</strong> {new_end_date}</li>
                </ul>

                <p><strong>Semua ciri kini tersedia:</strong></p>
                <ul>
                    <li>Dashboard: <span style="color: #10b981;">Aktif</span></li>
                    <li>Website: <span style="color: #10b981;">Aktif</span></li>
                    <li>Pesanan: <span style="color: #10b981;">Boleh diterima</span></li>
                </ul>

                <p style="text-align: center;">
                    <a href="{dashboard_url}" class="button">
                        Pergi ke Dashboard
                    </a>
                </p>

                <p>Terima kasih kerana terus menggunakan BinaApp!</p>
            </div>
            <div class="footer">
                <p>BinaApp - Platform Restoran Digital</p>
                <p>Soalan? Hubungi kami di {support_email}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
Assalamualaikum {name},

Akaun anda telah berjaya diaktifkan semula!

Butiran Langganan:
- Pakej: {plan_name}
- Tarikh Tamat Baru: {new_end_date}

Semua ciri kini tersedia:
- Dashboard: Aktif
- Website: Aktif
- Pesanan: Boleh diterima

Pergi ke Dashboard: {dashboard_url}

Terima kasih kerana terus menggunakan BinaApp!

BinaApp - Platform Restoran Digital
    """

    return {"subject": subject, "html": html, "text": text}


# Export all template functions
__all__ = [
    "render_reminder_5_days",
    "render_reminder_3_days",
    "render_expired_notice",
    "render_lock_warning",
    "render_locked_notice",
    "render_unlocked_notice",
    "get_base_styles",
]
