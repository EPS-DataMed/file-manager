import os
import mimetypes
import boto3

# Define the maximum file size permitted for uploads
KB = 1024
MB = 1024 * KB
MAX_FILE_SIZE = 200 * MB
MAX_FILE_SIZE_STRING = "200MB"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv('S3_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('S3_SECRET_ACCESS_KEY'),
    region_name=os.getenv('S3_REGION_NAME')
)

def is_pdf(filename: str) -> bool:
    mimetype, _ = mimetypes.guess_type(filename)
    return mimetype == 'application/pdf'

def file_size_within_bounds(contents) -> bool:
    size_in_bytes = len(contents)
    return size_in_bytes <= MAX_FILE_SIZE