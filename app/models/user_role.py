from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


ROLE_LEVELS = {
    UserRole.USER.value: 0,
    UserRole.ADMIN.value: 1,
    UserRole.SUPER_ADMIN.value: 2,
}