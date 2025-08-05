import os

# Project Root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# API Keys
OPENAI_API_KEY = "Your_API_Key_Here"
OPENAI_BASE_URL = "https://openrouter.ai/api/v1"

# Folder Paths
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'dataset', 'uploaded_files')
DATASET_FOLDER = os.path.join(PROJECT_ROOT, 'dataset')
RAG_DATA_FOLDER = os.path.join(PROJECT_ROOT, 'RAG_DATA')
