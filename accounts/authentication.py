from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class JWTAuthenticationWithCookie(JWTAuthentication):
    
    def authenticate(self, request):
        # get the token from the cookie
        token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE']) or None
        if token:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        return None