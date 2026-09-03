from app.core.security import (
    hash_password,
    verify_password,
)

password = "123456"
hashed = hash_password(password)

print(hashed)

print(
    verify_password(
        password,
        hashed,
    )
)

print(
    verify_password(
        "111111",
        hashed,
    )
)