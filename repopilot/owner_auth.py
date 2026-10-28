"""Single-owner login. Only hashes are persisted; no model/GitHub secrets reach clients."""

import hashlib
import hmac
import secrets
import threading
import time
from collections import deque

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from repopilot.migrations import sessions


def password_hash(password: str, salt: str | None = None) -> str:
    if not 16 <= len(password) <= 256:
        raise ValueError("Owner password must contain 16 to 256 characters")
    salt = salt or secrets.token_hex(16)
    result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return "scrypt$" + salt + "$" + result.hex()


class OwnerAuth:
    def __init__(self, engine: Engine, encoded_password: str):
        self.engine, self.encoded_password = engine, encoded_password
        self.attempts: deque[float] = deque()
        self.lock = threading.Lock()

    def login(self, password: str) -> str | None:
        # Globally bounded for the single owner, including concurrent attempts.
        with self.lock:
            timestamp = time.monotonic()
            while self.attempts and self.attempts[0] < timestamp - 60:
                self.attempts.popleft()
            if len(self.attempts) >= 5:
                raise ValueError("login_throttled")
            self.attempts.append(timestamp)
        if not self.encoded_password:
            return None
        try:
            scheme, salt, _ = self.encoded_password.split("$")
            valid = scheme == "scrypt" and hmac.compare_digest(
                password_hash(password, salt), self.encoded_password
            )
        except ValueError:
            valid = False
        if not valid:
            return None
        token = secrets.token_urlsafe(32)
        with self.engine.begin() as conn:
            conn.execute(delete(sessions).where(sessions.c.expires <= int(time.time())))
            conn.execute(
                sessions.insert().values(digest=self.digest(token), expires=int(time.time()) + 3600)
            )
        return token

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def valid(self, token: str) -> bool:
        if not 20 <= len(token) <= 100:
            return False
        with self.engine.connect() as conn:
            return (
                conn.execute(
                    select(sessions.c.digest).where(
                        sessions.c.digest == self.digest(token),
                        sessions.c.expires > int(time.time()),
                    )
                ).first()
                is not None
            )

    def logout(self, token: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(delete(sessions).where(sessions.c.digest == self.digest(token)))
