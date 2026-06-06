"""
Unit tests for the email-verification building blocks:
  - disposable-email domain detection
  - 6-digit code generation + hashing + constant-time verify
"""

from app.core.disposable_emails import is_disposable_email, get_email_domain
from app.core.verification import generate_code, hash_code, verify_code


class TestDisposableEmails:
    def test_known_disposable_blocked(self):
        assert is_disposable_email("foo@mailinator.com") is True
        assert is_disposable_email("bar@guerrillamail.com") is True
        assert is_disposable_email("x@yopmail.com") is True

    def test_regular_email_allowed(self):
        assert is_disposable_email("real@gmail.com") is False
        assert is_disposable_email("owner@mybiz.com.my") is False

    def test_case_insensitive(self):
        assert is_disposable_email("Foo@MailInator.com") is True

    def test_domain_extraction(self):
        assert get_email_domain("a@b.com") == "b.com"
        assert get_email_domain("no-at-sign") == ""


class TestVerificationCode:
    def test_generate_is_six_digits(self):
        for _ in range(50):
            code = generate_code()
            assert len(code) == 6
            assert code.isdigit()

    def test_hash_is_deterministic_and_user_bound(self):
        h1 = hash_code("user-1", "123456")
        h2 = hash_code("user-1", "123456")
        h3 = hash_code("user-2", "123456")
        assert h1 == h2          # same user + code -> same hash
        assert h1 != h3          # different user -> different hash

    def test_verify_matches_and_rejects(self):
        stored = hash_code("user-1", "654321")
        assert verify_code("user-1", "654321", stored) is True
        assert verify_code("user-1", "000000", stored) is False
        # Correct code but wrong user must not validate.
        assert verify_code("user-2", "654321", stored) is False

    def test_verify_strips_whitespace(self):
        stored = hash_code("user-1", "654321")
        assert verify_code("user-1", " 654321 ", stored) is True
