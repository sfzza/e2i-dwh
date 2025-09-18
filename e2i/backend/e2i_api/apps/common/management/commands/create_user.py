from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import getpass
import secrets

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a new user with specified role'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')
        parser.add_argument(
            '--role',
            type=str,
            choices=['admin', 'user'],
            default='user',
            help='Role for the user (admin or user)'
        )
        parser.add_argument('--email', type=str, help='Email address for the user')
        parser.add_argument('--password', type=str, help='Password for the user')
        parser.add_argument(
            '--generate-api-key',
            action='store_true',
            help='Generate an API key for the user'
        )

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        email = options.get('email')
        password = options.get('password')
        generate_api_key = options.get('generate_api_key', False)

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')

        # Get password if not provided
        if not password:
            password = getpass.getpass('Password: ')
            confirm_password = getpass.getpass('Confirm Password: ')
            if password != confirm_password:
                raise CommandError('Passwords do not match.')

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role
            )

            # Generate API key if requested
            api_key = None
            if generate_api_key:
                api_key = user.generate_api_key()

            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {role} user: {username}')
            )
            self.stdout.write(f'User ID: {user.id}')
            
            if email:
                self.stdout.write(f'Email: {email}')
                
            if api_key:
                self.stdout.write(f'API Key: {api_key}')
                self.stdout.write(
                    self.style.WARNING(
                        'Save this API key securely - it cannot be retrieved again!'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating user: {e}')
