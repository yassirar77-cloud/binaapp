"""
Customer lookup must match a phone number however it was stored.

`OrderCreate.validate_phone` rewrites `0176119872` to `+60176119872`
before the order flow stores it in `delivery_orders.customer_phone` and
`website_customers.phone`, while the chat flow stores the local
`0176119872` form. The lookup endpoints compared the digits-only string
against those columns with `.eq`, so a returning customer was always told
they were new and their saved address never pre-filled.
"""

from app.api.v1.endpoints.customers import _normalize_phone, _phone_candidates


def test_local_form_matches_every_stored_spelling():
    candidates = _phone_candidates(_normalize_phone("017-611 9872"))
    assert "+60176119872" in candidates   # what OrderCreate stores
    assert "0176119872" in candidates     # what the chat flow stores
    assert "60176119872" in candidates    # digits of the +60 form
    assert "176119872" in candidates      # bare national number


def test_international_form_matches_local_storage():
    candidates = _phone_candidates(_normalize_phone("+60 17-611 9872"))
    assert "0176119872" in candidates
    assert "+60176119872" in candidates


def test_same_number_yields_same_candidates_whatever_the_input():
    a = _phone_candidates(_normalize_phone("0176119872"))
    b = _phone_candidates(_normalize_phone("+60176119872"))
    c = _phone_candidates(_normalize_phone("60176119872"))
    assert a == b == c


def test_ten_digit_local_number_starting_with_60_is_not_truncated():
    # 0601234567 does not start with "60", so no country code is
    # stripped; the local form itself must stay a candidate.
    candidates = _phone_candidates(_normalize_phone("0601234567"))
    assert "0601234567" in candidates


def test_degenerate_input_does_not_crash():
    assert _phone_candidates("") == [""]
    assert _phone_candidates("0") == ["0"]
