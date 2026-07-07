import pytest

from app.core.config import settings
from app.services import mail


def test_console_backend(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "mail_backend", "console")
    mail.send("test@example.jp", "見積依頼を受け付けました", "本文")
    out = capsys.readouterr().out
    assert "test@example.jp" in out
    assert "見積依頼を受け付けました" in out
