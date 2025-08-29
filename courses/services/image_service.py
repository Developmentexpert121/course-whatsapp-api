import boto3
import os
import tempfile
from whatsapp_bot import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ImageService:
    @staticmethod
    def _get_s3_client():
        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
        )

    @staticmethod
    def upload_fileobj_to_s3(file_obj, s3_key, content_type=None, acl=None):
        """
        Upload a file object or a temp file path to S3 and return the public URL.
        file_obj may be:
         - Django InMemoryUploadedFile (has .chunks())
         - a local path (string)
        s3_key: full key inside bucket (e.g., "images/course/xxx/filename.jpg")
        """
        s3_client = ImageService._get_s3_client()
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        temp_path = None
        try:
            if hasattr(file_obj, "chunks"):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_obj.name)[1] or ".jpg")
                for chunk in file_obj.chunks():
                    tmp.write(chunk)
                tmp.flush()
                tmp.close()
                temp_path = tmp.name
                upload_source = temp_path
            elif isinstance(file_obj, str) and os.path.exists(file_obj):
                upload_source = file_obj
            else:
                if hasattr(file_obj, "read"):
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
                    tmp.write(file_obj.read())
                    tmp.flush()
                    tmp.close()
                    temp_path = tmp.name
                    upload_source = temp_path
                else:
                    raise ValueError("Unsupported file_obj type for S3 upload")

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            if acl:
                extra_args["ACL"] = acl

            s3_client.upload_file(upload_source, bucket_name, s3_key, ExtraArgs=extra_args if extra_args else None)

            file_url = f"https://{bucket_name}.s3.{settings.AWS_DEFAULT_REGION}.amazonaws.com/{s3_key}"
            return {"url": file_url, "key": s3_key}
        except Exception as e:
            logger.exception("S3 upload failed")
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    @staticmethod
    def delete_from_s3(s3_key):
        """Delete an object (if exists) from S3. Returns True on success."""
        try:
            s3_client = ImageService._get_s3_client()
            s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
            return True
        except Exception:
            logger.exception("Failed to delete object from S3: %s", s3_key)
            return False