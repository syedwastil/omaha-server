# your_project/settings/development.py

from .settings import *

DEBUG = True

ALLOWED_HOSTS = ['*','13.234.67.113']
CSRF_TRUSTED_ORIGINS = [
    'https://ranadrivingschool.org'
]
CSRF_COOKIE_SECURE = True  
CSRF_COOKIE_SAMESITE = 'Lax'
#Postgress db for production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
