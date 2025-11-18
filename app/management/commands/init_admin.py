import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize default admin user (idempotent)'

    def handle(self, *args, **options):
        # Get admin credentials from environment variables
        admin_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin')
        admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@admin.com')

        # Check if admin user already exists
        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin user "{admin_username}" already exists. Skipping creation.')
            )
            return

        # Create the admin user
        try:
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password
            )
            admin_user.is_verified = True
            admin_user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created admin user "{admin_username}" with default password. '
                    f'Please change the password after first login.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create admin user: {str(e)}')
            )
            raise
