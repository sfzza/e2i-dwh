from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo users for testing'

    def handle(self, *args, **options):
        demo_users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'password': 'admin123',
                'role': 'admin'
            },
            {
                'username': 'user1',
                'email': 'user1@example.com', 
                'password': 'user123',
                'role': 'user'
            },
            {
                'username': 'user2',
                'email': 'user2@example.com',
                'password': 'user123', 
                'role': 'user'
            }
        ]

        created_users = []
        
        for user_data in demo_users:
            username = user_data['username']
            
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'User {username} already exists, skipping...')
                continue

            user = User.objects.create_user(**user_data)
            api_key = user.generate_api_key()
            
            created_users.append({
                'user': user,
                'api_key': api_key
            })

        if created_users:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {len(created_users)} demo users')
            )
            
            self.stdout.write('\nDemo User Credentials:')
            self.stdout.write('-' * 80)
            
            for item in created_users:
                user = item['user']
                api_key = item['api_key']
                
                self.stdout.write(f'\n{user.role.upper()}: {user.username}')
                self.stdout.write(f'Password: admin123' if user.role == 'admin' else 'Password: user123')
                self.stdout.write(f'User ID: {user.id}')
                self.stdout.write(f'API Key: {api_key}')
                
            self.stdout.write('\n' + '-' * 80)
            self.stdout.write(
                self.style.WARNING(
                    'These are demo credentials - change passwords in production!'
                )
            )
        else:
            self.stdout.write('All demo users already exist.')
