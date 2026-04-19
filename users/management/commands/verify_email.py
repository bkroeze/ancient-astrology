from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Mark a user's email as verified in the database"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Email address to verify")

    def handle(self, *args, **options):
        email = options["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"No user found with email '{email}'")

        email_address, created = EmailAddress.objects.get_or_create(
            user=user,
            email=email,
            defaults={"verified": True, "primary": True},
        )

        if not created and not email_address.verified:
            email_address.verified = True
            email_address.primary = True
            email_address.save()
            self.stdout.write(self.style.SUCCESS(f"Verified email '{email}'"))
        elif created:
            self.stdout.write(
                self.style.SUCCESS(f"Created and verified email '{email}'")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Email '{email}' is already verified")
            )
