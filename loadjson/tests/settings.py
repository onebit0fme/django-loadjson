import django

DEBUG = True

ADMINS = ()

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example.sqlite',
    }
}

ALLOWED_HOSTS = []

TIME_ZONE = 'America/Toronto'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = ''
MEDIA_URL = ''

STATIC_ROOT = ''
STATIC_URL = '/static/'

STATICFILES_DIRS = ()

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = "secret_tests"

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'loadjson',
    'loadjson.tests'
)

LOAD_JSON = {
    'DATA_DIRS': [],
    'FINDER_CLASSES': [
        'loadjson.tests.finders.TestDataFinder'
    ],
    'ADAPTOR_CLASSES': [

    ]
}

# if django.VERSION[:2] < (1, 6):
#     TEST_RUNNER = 'discover_runner.DiscoverRunner'
#     INSTALLED_APPS += ('discover_runner',)
# else:
#     TEST_RUNNER = 'django.test.runner.DiscoverRunner'
