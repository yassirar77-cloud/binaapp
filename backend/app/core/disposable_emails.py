"""
Disposable / throwaway email-domain blocklist.

Used as a lightweight signup guard: we reject registrations whose email
domain is a well-known disposable/temporary-inbox provider. This is a
best-effort heuristic (the list is non-exhaustive and curated toward the
highest-volume offenders) — the real proof-of-ownership guard is the
6-digit verification code. Keep the list conservative to avoid blocking
legitimate users.

Domains are compared case-insensitively against the exact domain part of
the address (the bit after the last '@').
"""

# Curated set of common disposable / temporary email domains.
DISPOSABLE_EMAIL_DOMAINS: frozenset[str] = frozenset({
    "0-mail.com",
    "10minutemail.com",
    "10minutemail.net",
    "20minutemail.com",
    "33mail.com",
    "anonbox.net",
    "byom.de",
    "dispostable.com",
    "discard.email",
    "emailondeck.com",
    "fakeinbox.com",
    "fakemail.net",
    "fakemailgenerator.com",
    "getairmail.com",
    "getnada.com",
    "guerrillamail.com",
    "guerrillamail.net",
    "guerrillamail.org",
    "guerrillamailblock.com",
    "harakirimail.com",
    "inboxbear.com",
    "inboxkitten.com",
    "jetable.org",
    "mailcatch.com",
    "maildrop.cc",
    "mailinator.com",
    "mailnesia.com",
    "mailsac.com",
    "mintemail.com",
    "mohmal.com",
    "moakt.com",
    "mytemp.email",
    "nada.email",
    "nowmymail.com",
    "sharklasers.com",
    "spam4.me",
    "spamgourmet.com",
    "tempinbox.com",
    "tempmail.com",
    "tempmail.net",
    "temp-mail.org",
    "tempmailo.com",
    "tempr.email",
    "throwawaymail.com",
    "trashmail.com",
    "trashmail.de",
    "trashmail.net",
    "yopmail.com",
    "yopmail.fr",
    "yopmail.net",
    "wegwerfmail.de",
})


def get_email_domain(email: str) -> str:
    """Return the lowercased domain part of an email address ('' if none)."""
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].strip().lower()


def is_disposable_email(email: str) -> bool:
    """True if the email's domain is a known disposable/temporary provider."""
    return get_email_domain(email) in DISPOSABLE_EMAIL_DOMAINS
