import os

# valores falsos: los tests no tocan red, base de datos ni AWS
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/000000000000/test")
os.environ.setdefault("UPLOADS_BUCKET", "test-bucket")
