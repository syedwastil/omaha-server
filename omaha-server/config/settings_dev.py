# your_project/settings/development.py

from .settings import *

DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

print("In settings_dev.py")
# Development database (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Additional development-specific settings
