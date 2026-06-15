import pytest
from app.core.config import settings


def test_settings_has_database_url():
    """Settings should have a database_url"""
    assert hasattr(settings, 'database_url')
    assert settings.database_url == "sqlite+aiosqlite:///./acme_hr.db"


def test_settings_has_secret_key():
    """Settings should have a secret_key"""
    assert hasattr(settings, 'secret_key')
    assert settings.secret_key == "change-me-in-production"


def test_settings_has_algorithm():
    """Settings should have an algorithm"""
    assert hasattr(settings, 'algorithm')
    assert settings.algorithm == "HS256"


def test_settings_has_access_token_expire_minutes():
    """Settings should have access_token_expire_minutes"""
    assert hasattr(settings, 'access_token_expire_minutes')
    assert settings.access_token_expire_minutes == 30


def test_settings_has_refresh_token_expire_days():
    """Settings should have refresh_token_expire_days"""
    assert hasattr(settings, 'refresh_token_expire_days')
    assert settings.refresh_token_expire_days == 7


def test_settings_has_anthropic_api_key():
    """Settings should have anthropic_api_key"""
    assert hasattr(settings, 'anthropic_api_key')
    assert settings.anthropic_api_key == ""
