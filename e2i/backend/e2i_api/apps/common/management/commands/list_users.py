from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'List all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            choices=['admin', 'user'],
            help='Filter users by role'
        )

    def handle(self, *args, **options):
        role_filter = options.get('role')
        
        users = User.objects.all()
        if role_filter:
            users = users.filter(role=role_filter)

        users = users.order_by('role', 'username')

        if not users.exists():
            self.stdout.write('No users found.')
            return

        self.stdout.write('\nUsers:')
        self.stdout.write('-' * 80)
        self.stdout.write(f'{"Username":<20} {"Role":<10} {"Email":<25} {"Active":<8} {"API Key":<10}')
        self.stdout.write('-' * 80)

        for user in users:
            has_api_key = 'Yes' if user.api_key else 'No'
            active = 'Yes' if user.is_active else 'No'
            email = user.email or 'N/A'
            
            self.stdout.write(
                f'{user.username:<20} {user.role:<10} {email:<25} {active:<8} {has_api_key:<10}'
            )
        
        self.stdout.write('-' * 80)
        self.stdout.write(f'Total: {users.count()} users')
        
        # Show API keys if any users have them
        users_with_keys = users.filter(api_key__isnull=False)
        if users_with_keys.exists():
            self.stdout.write('\nAPI Keys:')
            self.stdout.write('-' * 80)
            for user in users_with_keys:
                self.stdout.write(f'{user.username}: {user.api_key}')
