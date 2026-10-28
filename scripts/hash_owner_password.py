"""Generate an owner password hash without storing or printing the password."""

from getpass import getpass

from repopilot.owner_auth import password_hash

print(password_hash(getpass("Owner password (16+ characters): ")))
