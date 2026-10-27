"""Unit tests for authentication."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.api.auth import _authenticate_user, register
from app.schemas.auth import UserRegister
from fastapi import HTTPException
from unittest.mock import MagicMock, patch
from app.api.auth import _authenticate_user, register
from app.schemas.auth import UserRegister
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

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


def test_public_registration_rejects_staff_roles():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.first.return_value = None
    payload = UserRegister(
        email='attacker@example.com',
        password='SafePass123!',
        full_name='Test User',
        role='admin',
    )

    with pytest.raises(HTTPException) as exc_info:
        register(payload, db)

    assert exc_info.value.status_code == 403
    db.add.assert_not_called()


def test_inactive_user_cannot_log_in():
    user = MagicMock(is_active=False, hashed_password='hashed')
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user

    with patch('app.api.auth.verify_password', return_value=True):
        with pytest.raises(HTTPException) as exc_info:
            _authenticate_user('disabled@example.com', 'password', db)

    assert exc_info.value.status_code == 403


def test_public_registration_rejects_staff_roles():
    db = MagicMock()
    payload = UserRegister(
        email='attacker@example.com',
        password='SafePass123!',
        full_name='Test User',
        role='admin',
    )

    with pytest.raises(HTTPException) as exc_info:
        register(payload, db)

    assert exc_info.value.status_code == 403
    db.add.assert_not_called()


def test_inactive_user_cannot_log_in():
    user = MagicMock(is_active=False, hashed_password='hashed')
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user

    with patch('app.api.auth.verify_password', return_value=True):
        with pytest.raises(HTTPException) as exc_info:
            _authenticate_user('disabled@example.com', 'password', db)

    assert exc_info.value.status_code == 403
