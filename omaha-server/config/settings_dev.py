# your_project/settings/development.py

from .settings import *

DEBUG = True
print('static root is :',STATIC_ROOT)
print('base_dir is :',BASE_DIR)
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
# Development database (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Additional development-specific settings
