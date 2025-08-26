import tempfile
import boto3
import os
from django.template.loader import render_to_string
from weasyprint import HTML
from whatsapp_bot import settings
from datetime import datetime
from whatsapp.models import UserEnrollment


class CertificateService:
    @staticmethod
    def generate_certificate(student_name, course_name, completed_at):
        """
        Generate a PDF certificate for the given student and course.
        Returns the local file path.
        """
        html_string = render_to_string(
            "certificate_template.html",
            {
                "student_name": student_name,
                "course_name": course_name,
                "date": completed_at,
                "date": datetime.now().strftime("%B %d, %Y"),
            },
        )

        html = HTML(string=html_string)
        pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        html.write_pdf(target=pdf_file.name)

        return pdf_file.name  # Path to generated PDF

    @staticmethod
    def upload_to_s3(file_path, s3_key):
        """
        Uploads the given file to S3 and returns the public URL.
        s3_key is the path/key in the bucket (e.g., 'certificates/cert1.pdf')
        """
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
        )

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        # Upload file
        s3_client.upload_file(
            file_path, bucket_name, s3_key, ExtraArgs={"ContentType": "application/pdf"}
        )

        # Generate public URL
        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_DEFAULT_REGION}.amazonaws.com/{s3_key}"

        return file_url

    @staticmethod
    def generate_and_upload_certificate(enrollment: UserEnrollment):
        """
        Generate certificate for an enrollment, upload to S3, and update enrollment record.
        Returns the S3 URL of the certificate.

        Args:
            enrollment (UserEnrollment): The enrollment object

        Returns:
            str: S3 URL of the generated certificate
        """
        # Generate certificate
        student_name = enrollment.user.full_name or enrollment.user.whatsapp_name
        course_name = enrollment.course.course_name
        completed_at = enrollment.completed_at
        pdf_path = CertificateService.generate_certificate(
            student_name, course_name, completed_at
        )

        try:
            # Create S3 key with a structured path
            s3_key = f"certificates/{enrollment.user.id}/{enrollment.course.course_id}/{datetime.now().strftime('%Y%m%d')}.pdf"

            # Upload to S3
            certificate_url = CertificateService.upload_to_s3(pdf_path, s3_key)

            # Update enrollment record
            enrollment.certificate_earned = True
            enrollment.certificate_url = certificate_url
            enrollment.save()

            return certificate_url

        except Exception as e:
            # Log error and cleanup
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            raise Exception(f"Failed to generate and upload certificate: {str(e)}")

        finally:
            # Cleanup temporary file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
