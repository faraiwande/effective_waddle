import boto3
import uuid
import os
from io import BytesIO
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app


s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("S3_REGION")
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_IMAGE_SIZE_MB = 2
MAX_IMAGE_DIMENSION = 512

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_image_to_s3(file_obj, folder="profile_pics"):
    if not allowed_file(file_obj.filename):
        raise ValueError("Only .png, .jpg, .jpeg files are allowed")

    file_obj.seek(0, os.SEEK_END)
    size_in_mb = file_obj.tell() / (1024 * 1024)
    file_obj.seek(0)
    if size_in_mb > MAX_IMAGE_SIZE_MB:
        raise ValueError("Image must be less than 2MB")

    image = Image.open(file_obj)
    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))

    buffer = BytesIO()
    format = 'JPEG' if image.format.lower() in ['jpeg', 'jpg'] else 'PNG'
    image.save(buffer, format=format)
    buffer.seek(0)

    ext = format.lower()
    key = f"{folder}/{uuid.uuid4()}.{ext}"

    s3.upload_fileobj(
        Fileobj=buffer,
        Bucket=BUCKET_NAME,
        Key=key,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": f"image/{ext}"
        }
    )

    return f"https://{BUCKET_NAME}.s3.{os.getenv('S3_REGION')}.amazonaws.com/{key}"



