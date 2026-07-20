import secrets

JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_token(n_bytes=16):
    return secrets.token_urlsafe(n_bytes)


def generate_join_code(length=4):
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))