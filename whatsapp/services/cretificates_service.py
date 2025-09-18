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
    def generate_badge(student_name, badge_title, badge_date):
        """
        Generate a badge PDF with inline SVG.
        """
        if isinstance(badge_date, str):
            badge_date = datetime.strptime(
                badge_date, "%Y-%m-%d"
            )  # adjust format if needed

        # Format date as dd-mm-yyyy
        formatted_date = badge_date.strftime("%d-%m-%Y")

        # Your SVG code as a Python string
        svg_code = f"""
        <svg width="500" height="500" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg">
            <!-- Gradient Background Circle -->
            <defs>
                <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="10%" style="stop-color:#81c142;stop-opacity:1" />
                    <stop offset="90%" style="stop-color:#ff7900;stop-opacity:1" />
                </linearGradient>
            </defs>
            <circle cx="250" cy="250" r="240" fill="url(#grad)" />
            
            <!-- Logo Text with parallelograms -->
            <text x="43%" y="140" font-family="Arial, sans-serif" font-size="40" font-weight="bold" text-anchor="middle" fill="black">N</text>
            <g transform="translate(240,112)">
                <polygon points="0,0 20,0 15,5 -5,5" fill="#ff7900"/>
                <polygon points="0,10 20,10 15,15 -5,15" fill="#ff7900"/>
                <polygon points="0,20 20,20 15,25 -5,25" fill="#ff7900"/>
            </g>
            <text x="59%" y="140" font-family="Arial, sans-serif" font-size="40" font-weight="bold" text-anchor="middle" fill="black">X T</text>
            <text x="39%" y="180" font-family="Arial, sans-serif" font-size="40" font-weight="bold" text-anchor="middle" fill="black">S T</text>
            <g transform="translate(240,152)">
                <polygon points="0,0 20,0 15,5 -5,5" fill="#81c142"/>
                <polygon points="0,10 20,10 15,15 -5,15" fill="#81c142"/>
                <polygon points="0,20 20,20 15,25 -5,25" fill="#81c142"/>
            </g>
            <text x="56%" y="180" font-family="Arial, sans-serif" font-size="40" font-weight="bold" text-anchor="middle" fill="black">P</text>
            <text x="50%" y="205" font-family="Arial, sans-serif" font-size="19" text-anchor="middle" fill="black">FOUNDATION</text>
            <text id="badgeTitle" x="50%" y="300" font-style="italic" font-family="Brush Script MT, cursive" font-size="36" text-anchor="middle" fill="black">{badge_title}</text>
            <text x="50%" y="350" font-style="italic" font-family="Brush Script MT, cursive" font-size="22" text-anchor="middle" fill="black">Next Step Foundation</text>
            <text id="badgeDate" x="50%" y="390" font-style="italic" font-family="Brush Script MT, cursive" font-size="22" text-anchor="middle" fill="black">{formatted_date}</text>
        </svg>
        """

        html_string = render_to_string(
            "badge_template.html",
            {
                "student_name": student_name,
                "svg_code": svg_code,
            },
        )

        html = HTML(string=html_string)
        pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        html.write_pdf(target=pdf_file.name)

        return pdf_file.name

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

    @staticmethod
    def generate_and_upload_badge(enrollment: UserEnrollment):
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
        pdf_path = CertificateService.generate_badge(
            student_name, course_name, completed_at
        )

        try:
            # Create S3 key with a structured path
            s3_key = f"badges/{enrollment.user.id}/{enrollment.course.course_id}/{datetime.now().strftime('%Y%m%d')}.pdf"

            # Upload to S3
            badge_url = CertificateService.upload_to_s3(pdf_path, s3_key)

            enrollment.badge_url = badge_url
            enrollment.save()

            return badge_url

        except Exception as e:
            # Log error and cleanup
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            raise Exception(f"Failed to generate and upload certificate: {str(e)}")

        finally:
            # Cleanup temporary file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
