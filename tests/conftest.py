# tests/conftest.py
import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def _allow_django_sync_in_async():
    # Permite chamadas síncronas do Django quando o teste roda em loop async (Playwright)
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
