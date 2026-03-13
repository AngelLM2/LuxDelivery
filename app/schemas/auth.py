from pydantic import BaseModel, Field, field_validator

PASSWORD_MAX_BCRYPT_BYTES = 72
PASSWORD_MAX_BCRYPT_BYTES_MESSAGE = (
    "Senha muito longa para o algoritmo atual. Use no maximo 72 bytes."
)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_bcrypt_bytes(cls, password: str) -> str:
        if len(password.encode("utf-8")) > PASSWORD_MAX_BCRYPT_BYTES:
            raise ValueError(PASSWORD_MAX_BCRYPT_BYTES_MESSAGE)
        return password


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
