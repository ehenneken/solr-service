import os

SOLR_SERVICE_VERSION = 'v4.10'
SOLR_SERVICE_URL = os.environ.get('SOLR_SERVICE_URL', 'http://localhost:8983/solr')
SOLR_SERVICE_TVRH_HANDLER = SOLR_SERVICE_URL + '/tvrh'
SOLR_SERVICE_SEARCH_HANDLER = SOLR_SERVICE_URL + '/select'
SOLR_SERVICE_QTREE_HANDLER = SOLR_SERVICE_URL + '/qtree'
SOLR_SERVICE_BIGQUERY_HANDLER = SOLR_SERVICE_URL + '/bigquery'
SOLR_SERVICE_FORWARD_COOKIE_NAME = 'session'
SOLR_SERVICE_DISALLOWED_FIELDS = ['body', 'full', 'reader']
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_BINDS = {
    'solr_service':        'sqlite:///'
}
SOLR_SERVICE_ALLOWED_FIELDS = [
    'abstract', 'ack', 'aff', 'alternate_bibcode', 'alternate_title',
    'arxiv_class', 'author', 'bibcode', 'bibgroup', 'bibstem',
    'citation_count', 'copyright', 'data', 'database', 'doctype', 'doi',
    'first_author', 'grant', 'id', 'identifier', 'indexstamp', 'issue',
    'keyword', 'lang', 'orcid_other', 'orcid_pub', 'orcid_user', 'page',
    'property', 'pub', 'pubdate', 'read_count', 'title', 'vizier', 'volume',
    'year'
]

SOLR_SERVICE_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(levelname)s\t%(process)d '
                      '[%(asctime)s]:\t%(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S',
        }
    },
    'handlers': {
        'file': {
            'formatter': 'default',
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/tmp/solr_service_app.log',
        },
        'console': {
            'formatter': 'default',
            'level': 'INFO',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
