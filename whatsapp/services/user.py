import logging
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework import status
from whatsapp.models import WhatsappUser


logger = logging.getLogger(__name__)


class WhatsappUserService:
    @classmethod
    def get_all_users(cls):
        """Retrieve all WhatsApp users"""
        try:
            users = WhatsappUser.objects.all()
            return {"success": True, "data": [cls.to_dict(user) for user in users]}
        except Exception as e:
            logger.exception("Error retrieving users")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def get_user(cls, whatsapp_id):
        """Retrieve a WhatsApp user by ID"""
        try:
            user = WhatsappUser.objects.get(whatsapp_id=whatsapp_id)
            return {"success": True, "data": cls.to_dict(user), "error": None}
        except WhatsappUser.DoesNotExist:
            return {"success": False, "data": None, "error": "user not found"}

    @classmethod
    def resgiter_user(cls, data):
        """Register a new WhatsApp user"""
        try:
            whatsapp_id = data.get("whatsapp_id")
            whatsapp_name = data.get("whatsapp_name")
            registration_date = now()
            last_active = now()
            full_name = data.get("full_name", "")
            email = data.get("email", "")
            age = data.get("age", None)
            gender = data.get("gender", "")
            education_level = data.get("education_level", "")
            current_institution = data.get("current_institution", "")
            interests = data.get("interests", [])
            timezone = data.get("timezone", "")
            preferred_language = data.get("preferred_language", "")
            message_count = data.get("message_count", 1)
            response_rate = data.get("response_rate", 0.0)
            completion_rate = data.get("completion_rate", 0.0)
            account_status = data.get("account_status", "active")
            subscription_type = data.get("subscription_type", "free")
            tags = data.get("tags", [])
            notes = data.get("notes", "")

            user, created = WhatsappUser.objects.update_or_create(
                whatsapp_id=whatsapp_id,
                defaults={
                    "whatsapp_name": whatsapp_name,
                    "registration_date": registration_date,
                    "last_active": last_active,
                    "full_name": full_name,
                    "email": email,
                    "age": age,
                    "gender": gender,
                    "education_level": education_level,
                    "current_institution": current_institution,
                    "interests": interests,
                    "timezone": timezone,
                    "preferred_language": preferred_language,
                    "message_count": message_count,
                    "response_rate": response_rate,
                    "completion_rate": completion_rate,
                    "account_status": account_status,
                    "subscription_type": subscription_type,
                    "tags": tags,
                    "notes": notes,
                },
            )
            if user:
                return {"success": True, "data": cls.to_dict(user), "error": None}
            if created:
                return {"success": True, "data": cls.to_dict(created), "error": None}
        except Exception as e:
            logger.exception("Error registering user")
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def update_user(cls, data):
        """Update an existing WhatsApp user"""
        try:
            whatsapp_id = data.get("whatsapp_id")
            user = WhatsappUser.objects.get(whatsapp_id=whatsapp_id)
            user.whatsapp_name = data.get("whatsapp_name", user.whatsapp_name)
            user.full_name = data.get("full_name", user.full_name)
            user.email = data.get("email", user.email)
            user.age = data.get("age", user.age)
            user.gender = data.get("gender", user.gender)
            user.last_active = now()
            user.education_level = data.get("education_level", "")
            user.current_institution = data.get("current_institution", "")
            user.interests = data.get("interests", [])
            user.timezone = data.get("timezone", "")
            user.preferred_language = data.get("preferred_language", "")
            user.message_count = data.get("message_count", 1)
            user.response_rate = data.get("response_rate", 0.0)
            user.completion_rate = data.get("completion_rate", 0.0)
            user.account_status = data.get("account_status", "active")
            user.subscription_type = data.get("subscription_type", "free")
            user.tags = data.get("tags", [])
            user.notes = data.get("notes", "")
            user.save()
            return {"success": True, "data": cls.to_dict(user), "error": None}
        except WhatsappUser.DoesNotExist:
            return {"success": True, "data": None, "error": "User not found"}
        except Exception as e:
            logger.exception("Error updating user")
            return {"success": True, "data": None, "error": "Internal server error"}

    @classmethod
    def delete_user(cls, whatsapp_id):
        """Delete a WhatsApp user"""
        try:
            user = WhatsappUser.objects.get(whatsapp_id=whatsapp_id)
            if not user:
                return {"success": False, "data": None, "error": "User not found"}
            res = user.delete()
            print("user delete report: ", res)
            return {"success": True, "data": whatsapp_id, "error": None}
        except WhatsappUser.DoesNotExist:
            return {"success": False, "data": None, "error": "User not found"}
        except Exception as e:
            logger.exception("Error deleting user")
            return {"success": False, "data": None, "error": "Internal server error"}

    @classmethod
    def delete_users_bulk(cls, whatsapp_ids):
        """Delete multiple WhatsApp users"""
        try:
            users = WhatsappUser.objects.filter(whatsapp_id__in=whatsapp_ids)
            deleted_count, _ = users.delete()
            return {"success": True, "data": deleted_count, "error": None}
        except Exception as e:
            logger.exception("Error deleting users in bulk")
            return {"success": False, "data": None, "error": "Internal server error"}

    @classmethod
    def to_dict(cls, self):
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "whatsappId": self.whatsapp_id,
            "whatsappName": self.whatsapp_name,
            "registrationDate": self.registration_date.isoformat(),
            "lastActive": self.last_active.isoformat(),
            "fullName": self.full_name,
            "email": self.email,
            "age": self.age,
            "gender": self.gender,
            "currentInstitution": self.current_institution,
            "interests": self.interests,
            "timezone": self.timezone,
            "preferredLanguage": self.preferred_language,
            "enrolledCourses": self.enrolled_courses,
            "isActive": self.is_active,
            "messageCount": self.message_count,
            "responseRate": self.response_rate,
            "completionRate": self.completion_rate,
            "accountStatus": self.account_status,
            "subscriptionType": self.subscription_type,
            "tags": self.tags,
            "notes": self.notes,
        }
