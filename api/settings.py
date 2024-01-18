import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# if we are running in appengine env
GAE_APP_NAME = os.getenv('GAE_APPLICATION', '')
if GAE_APP_NAME:
    split = GAE_APP_NAME.split('~')
    PROJECT_ID = split[1] if len(split) > 1 else 'local'

DEBUG = os.getenv('DEBUG', False) == 'True'

DEV = DEBUG

SECRET_KEY = os.getenv('SECRET_KEY')

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'corsheaders',
]

MIDDLEWARE = [
    # 'app.middleware.CORSMiddleware',
    # this should be only for the web stats endpoint
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.middleware.MyExceptionMiddleware',
]

ROOT_URLCONF = 'api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'api.wsgi.application'

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = [
    'http://localhost',
    'https://peermetrics.appspot.com',
    'https://www.peermetrics.io',
    'https://www.peermetrics.dev',
]

SESSION_COOKIE_NAME = 'pmsession'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        # 'HOST': '127.0.0.1',
        # 'PORT': 3306,
        'HOST': os.getenv('DATABASE_HOST'),
        'PORT': os.getenv('DATABASE_PORT'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'NAME': os.getenv('DATABASE_NAME'),
        'CONN_MAX_AGE': int(os.getenv('CONN_MAX_AGE')),
    },
}

if os.getenv('REDIS_HOST'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_HOST'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                'IGNORE_EXCEPTIONS': True,
                'SOCKET_TIMEOUT': 1,
                'SOCKET_CONNECT_TIMEOUT': 1,
            },
        },
    }

# we should make this work
# DJANGO_REDIS_LOG_IGNORE_EXCEPTIONS = True

# redis key TTL, 1 hour
REDIS_KEY_TTL = 60 * 60

AUTH_USER_MODEL = 'app.User'

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

STATIC_URL = '/static/'
STATIC_ROOT =  '/app/static'

# Other App defaults
DEFAULT_INTERVAL = 10000

BATCH_CONNECTION_REQUESTS = False

INIT_TOKEN_SECRET = os.getenv('INIT_TOKEN_SECRET')
SESSION_TOKEN_SECRET = os.getenv('SESSION_TOKEN_SECRET')

INIT_TOKEN_LIFESPAN = 86400  # 24h
SESSION_TOKEN_LIFESPAN = 86400  # 24h

DEFAULT_BILLING_PERIOD_DAYS = 31

EVENT_CATEGORIES = {
    'browser': 'B',
    'getUserMedia': 'M',
    'connection': 'C',
    'track': 'T',
    'stats': 'S',
}

USE_EXTERNAL_GEOIP_PROVIDER = os.getenv('USE_EXTERNAL_GEOIP_PROVIDER', False) == 'True'

# geo ip data
GEOIP_PROVIDERS = [{
    'name': 'ipstack',
    'access_key': os.getenv('IPSTACK_ACCESS_KEY'),
    'url': os.getenv('IPSTACK_URL'),
}]

MAX_SEARCH_RESULTS = 5

RATELIMIT_FAIL_OPEN = True

WEB_DOMAIN = os.getenv('WEB_DOMAIN')

LINKS = {
    'conference': 'https://{}/conference/'.format(WEB_DOMAIN),
    'participant': 'https://{}/participant/'.format(WEB_DOMAIN),
}

# task queue settings
USE_GOOGLE_TASK_QUEUE = os.getenv('USE_GOOGLE_TASK_QUEUE', False) == 'True'
QUEUE_NAME = os.getenv('GOOGLE_TASK_QUEUE_NAME')
APP_LOCATION = os.getenv('APP_ENGINE_LOCATION')
TASK_QUEUE_DOMAIN = os.getenv('TASK_QUEUE_DOMAIN')

POST_CONFERENCE_CLEANUP = os.getenv('POST_CONFERENCE_CLEANUP', False) == 'True'

USE_GOOGLE_CLOUD_LOGGING = os.getenv('USE_GOOGLE_CLOUD_LOGGING', False) == 'True'

if USE_GOOGLE_CLOUD_LOGGING:
    try:
        # Imports the Cloud Logging client library
        import google.cloud.logging

        # Instantiates a client
        client = google.cloud.logging.Client()

        # Retrieves a Cloud Logging handler based on the environment
        # you're running in and integrates the handler with the
        # Python logging module. By default this captures all logs
        # at INFO level and higher
        client.get_default_handler()
        client.setup_logging()
    except Exception as e:
        pass