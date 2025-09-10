import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE = 'files.db'
    UPLOAD_FOLDER = 'files'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024 * 1024  # 4GB limit