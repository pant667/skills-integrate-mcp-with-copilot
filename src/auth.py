import base64
import binascii
import getpass
import hashlib
import json
import secrets
from pathlib import Path


PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"


class TeacherConfigurationError(ValueError):
    pass


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt_text}${digest_text}"


def _parse_password_hash(password_hash: str) -> tuple[int, bytes, bytes]:
    try:
        prefix, iterations_text, salt_text, digest_text = password_hash.split("$")
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_text, altchars=b"-_", validate=True)
        digest = base64.b64decode(digest_text, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Malformed password hash") from exc

    if (
        prefix != PASSWORD_HASH_PREFIX
        or not PASSWORD_HASH_ITERATIONS <= iterations <= 1_200_000
        or len(salt) < 16
        or len(digest) != hashlib.sha256().digest_size
    ):
        raise ValueError("Unsupported password hash")

    return iterations, salt, digest


def verify_password(password: str, password_hash: str) -> bool:
    try:
        iterations, salt, expected_digest = _parse_password_hash(password_hash)
    except ValueError:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return secrets.compare_digest(actual_digest, expected_digest)


def load_teacher_credentials(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TeacherConfigurationError(
            f"Teacher credentials file does not exist: {path}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise TeacherConfigurationError(
            f"Unable to read teacher credentials file: {path}"
        ) from exc

    if not isinstance(data, list):
        raise TeacherConfigurationError("Teacher credentials must be a JSON array")

    credentials = {}
    for entry in data:
        if not isinstance(entry, dict):
            raise TeacherConfigurationError("Each teacher entry must be an object")

        username = entry.get("username")
        password_hash = entry.get("password_hash")
        if not isinstance(username, str) or not username.strip():
            raise TeacherConfigurationError("Each teacher needs a non-empty username")
        if not isinstance(password_hash, str):
            raise TeacherConfigurationError(f"Teacher {username!r} has no password hash")
        if username in credentials:
            raise TeacherConfigurationError(f"Duplicate teacher username: {username}")
        try:
            _parse_password_hash(password_hash)
        except ValueError as exc:
            raise TeacherConfigurationError(
                f"Teacher {username!r} has an invalid password hash"
            ) from exc

        credentials[username] = password_hash

    return credentials


def main():
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username must not be empty")

    password = getpass.getpass("Teacher password: ")
    teacher = {"username": username, "password_hash": hash_password(password)}
    print(json.dumps(teacher, indent=2))


if __name__ == "__main__":
    main()
