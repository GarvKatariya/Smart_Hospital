"""Unit tests for authentication."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    password = 'TestPassword123'
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password('wrong', hashed)

def test_jwt_token():
    data = {'sub': 'test@example.com', 'role': 'patient'}
    token = create_access_token(data)
    assert token
    decoded = decode_access_token(token)
    assert decoded['sub'] == 'test@example.com'
    assert decoded['role'] == 'patient'
