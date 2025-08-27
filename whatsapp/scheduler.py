import os
from django.utils import timezone
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from whatsapp.models import AutomationRule, UserMessageLog, WhatsappUser
from whatsapp.services.messaging import WhatsAppService


def check_inactive_users():
    print(">>> Running check_inactive_users job...")

    now = timezone.now()
    print(f"Current time: {now}")

    rules = AutomationRule.objects.filter(is_active=True)
    print(f"Found {rules.count()} active automation rules.")

    for rule in rules:
        print(f"\nProcessing rule: {rule.id} | Days Inactive: {rule.days_inactive}")

        cutoff = now - timedelta(days=rule.days_inactive)
        print(f"Cutoff date for inactivity: {cutoff}")

        inactive_users = WhatsappUser.objects.filter(last_active__lt=cutoff)
        print(f"Initially found {inactive_users.count()} inactive users.")

        # Exclude users who received a message recently
        recent_recipients = UserMessageLog.objects.filter(
            rule=rule, sent_at__gte=now - timedelta(days=7)
        ).values_list("user_id", flat=True)

        print(
            f"Users who already received a message in last 7 days: {len(recent_recipients)}"
        )

        inactive_users = inactive_users.exclude(id__in=recent_recipients)
        print(f"Eligible inactive users after exclusion: {inactive_users.count()}")

        for user in inactive_users:
            days_inactive = (
                (now - user.last_active).days
                if user.last_active
                else rule.days_inactive
            )
            print(
                f"User: {user.id} | WhatsApp ID: {user.whatsapp_id} | Days Inactive: {days_inactive}"
            )

            try:
                formatted_message = rule.message_template.format(
                    name=user.full_name,
                    days=days_inactive,
                )

                print(f"Formatted message for user {user.id}: {formatted_message}")

                # Send message
                WhatsAppService.send_message(
                    os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
                    user.whatsapp_id,
                    formatted_message,
                )
                print(f"✅ Sent reminder to {user.whatsapp_id}")

                # Log the message
                UserMessageLog.objects.create(
                    user=user, rule=rule, message_content=formatted_message, sent_at=now
                )
                print(f"📌 Logged message for user {user.id}")

            except Exception as e:
                print(f"❌ Failed to send message to {user.whatsapp_id}: {e}")

    print(">>> check_inactive_users job completed.\n")


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_inactive_users, "interval", hours=6, id="inactive_user_job")
    scheduler.start()
