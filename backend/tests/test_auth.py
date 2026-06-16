import pytest
from datetime import timedelta
from app.auth.utils import hash_password, verify_password, create_access_token, decode_token


def test_hash_and_verify_password():
    plain = "supersecret123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_and_decode_access_token():
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data, expires_delta=timedelta(minutes=30))
    payload = decode_token(token)
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "admin"


def test_expired_token_raises():
    data = {"sub": "user@example.com"}
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        decode_token(token)
