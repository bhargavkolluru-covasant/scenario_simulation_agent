from app.config.settings import settings
from app.services.token_service import TokenService

print("TOKEN:")
print(settings.access_token)

meta = TokenService.decode_token(settings.access_token)

print("\nEXPIRES AT:")
print(meta.expires_at)

print("\nEXPIRED:")
print(meta.is_expired)