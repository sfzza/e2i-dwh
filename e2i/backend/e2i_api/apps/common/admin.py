# e2i_api/apps/common/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserSession
import secrets


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form for Django admin."""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom user change form for Django admin."""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'is_active')


class UserSessionInline(admin.TabularInline):
    """Inline admin for user sessions."""
    model = UserSession
    extra = 0
    readonly_fields = ('session_token', 'created_at', 'expires_at', 'last_accessed', 'ip_address', 'user_agent')
    fields = ('session_token', 'is_active', 'created_at', 'expires_at', 'last_accessed', 'ip_address')
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin interface for User model."""
    
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = (
        'username', 
        'email', 
        'role', 
        'is_active', 
        'has_api_key_display',
        'active_sessions_count',
        'created_at',
        'last_login'
    )
    
    list_filter = (
        'role', 
        'is_active', 
        'created_at',
        'last_login'
    )
    
    search_fields = ('username', 'email')
    
    ordering = ('-created_at',)
    
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at', 
        'last_login',
        'api_key_display',
        'active_sessions_count',
        'password_change_link'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'username', 'email', 'role')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at', 'last_login')
        }),
        ('Authentication', {
            'fields': ('api_key_display', 'active_sessions_count', 'password_change_link'),
            'description': 'API keys and session management'
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2'),
        }),
    )
    
    inlines = [UserSessionInline]
    
    actions = ['generate_api_keys', 'revoke_api_keys', 'activate_users', 'deactivate_users']

    def has_api_key_display(self, obj):
        """Display whether user has an API key."""
        if obj.api_key:
            return format_html(
                '<span style="color: green;">✓ Yes</span>'
            )
        return format_html(
            '<span style="color: red;">✗ No</span>'
        )
    has_api_key_display.short_description = 'Has API Key'
    
    def api_key_display(self, obj):
        """Display API key with copy button."""
        if obj.api_key:
            return format_html(
                '<div style="font-family: monospace; background: #f8f9fa; padding: 8px; border-radius: 4px;">'
                '{}<br>'
                '<button onclick="navigator.clipboard.writeText(\'{}\')" '
                'style="margin-top: 5px; padding: 2px 8px; font-size: 11px;">Copy to Clipboard</button>'
                '</div>',
                obj.api_key,
                obj.api_key
            )
        return format_html(
            '<em>No API key generated</em><br>'
            '<a href="#" onclick="if(confirm(\'Generate API key for this user?\')) {'
            'fetch(\'/admin/generate_api_key/{}/\', {{method: \'POST\', headers: {{\'X-CSRFToken\': document.querySelector(\'[name=csrfmiddlewaretoken]\').value}}}}) '
            '.then(() => location.reload()); return false;}" '
            'style="color: #007cba;">Generate API Key</a>',
            obj.pk
        )
    api_key_display.short_description = 'API Key'
    
    def active_sessions_count(self, obj):
        """Display count of active sessions."""
        count = obj.sessions.filter(is_active=True).count()
        if count > 0:
            return format_html(
                '<span style="color: green;">{} active</span>',
                count
            )
        return format_html(
            '<span style="color: #666;">0 active</span>'
        )
    active_sessions_count.short_description = 'Active Sessions'
    
    def password_change_link(self, obj):
        """Link to change password."""
        if obj.pk:
            url = reverse('admin:auth_user_password_change', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button">Change Password</a>',
                url
            )
        return "Save user first"
    password_change_link.short_description = 'Password'

    def generate_api_keys(self, request, queryset):
        """Admin action to generate API keys for selected users."""
        count = 0
        for user in queryset:
            if not user.api_key:
                user.generate_api_key()
                count += 1
        
        self.message_user(
            request,
            f'Generated API keys for {count} user(s).'
        )
    generate_api_keys.short_description = "Generate API keys for selected users"
    
    def revoke_api_keys(self, request, queryset):
        """Admin action to revoke API keys for selected users."""
        count = queryset.filter(api_key__isnull=False).update(api_key=None)
        self.message_user(
            request,
            f'Revoked API keys for {count} user(s).'
        )
    revoke_api_keys.short_description = "Revoke API keys for selected users"
    
    def activate_users(self, request, queryset):
        """Admin action to activate selected users."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Activated {count} user(s).'
        )
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Admin action to deactivate selected users."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Deactivated {count} user(s).'
        )
    deactivate_users.short_description = "Deactivate selected users"


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin interface for UserSession model."""
    
    list_display = (
        'user', 
        'session_token_short', 
        'is_active', 
        'created_at', 
        'expires_at',
        'last_accessed',
        'ip_address'
    )
    
    list_filter = (
        'is_active', 
        'created_at', 
        'expires_at'
    )
    
    search_fields = (
        'user__username', 
        'user__email', 
        'ip_address',
        'session_token'
    )
    
    readonly_fields = (
        'id',
        'session_token', 
        'created_at', 
        'user_agent_display'
    )
    
    fields = (
        'id',
        'user', 
        'session_token', 
        'is_active',
        'created_at', 
        'expires_at', 
        'last_accessed',
        'ip_address',
        'user_agent_display'
    )
    
    actions = ['deactivate_sessions', 'extend_sessions']
    
    def session_token_short(self, obj):
        """Display shortened session token."""
        if obj.session_token:
            return f"{obj.session_token[:8]}...{obj.session_token[-8:]}"
        return "None"
    session_token_short.short_description = 'Session Token'
    
    def user_agent_display(self, obj):
        """Display user agent in a readable format."""
        if obj.user_agent:
            # Truncate long user agent strings
            if len(obj.user_agent) > 100:
                return format_html(
                    '<div style="max-width: 300px; word-wrap: break-word;">'
                    '{}<br><em>...truncated</em>'
                    '</div>',
                    obj.user_agent[:100]
                )
            return format_html(
                '<div style="max-width: 300px; word-wrap: break-word;">{}</div>',
                obj.user_agent
            )
        return "Unknown"
    user_agent_display.short_description = 'User Agent'
    
    def deactivate_sessions(self, request, queryset):
        """Admin action to deactivate selected sessions."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Deactivated {count} session(s).'
        )
    deactivate_sessions.short_description = "Deactivate selected sessions"
    
    def extend_sessions(self, request, queryset):
        """Admin action to extend selected sessions by 7 days."""
        from datetime import timedelta
        from django.utils import timezone
        
        count = 0
        for session in queryset.filter(is_active=True):
            session.expires_at = timezone.now() + timedelta(days=7)
            session.save()
            count += 1
            
        self.message_user(
            request,
            f'Extended {count} session(s) by 7 days.'
        )
    extend_sessions.short_description = "Extend selected sessions by 7 days"


# Customize Django admin site
admin.site.site_header = "E2I Administration"
admin.site.site_title = "E2I Admin"
admin.site.index_title = "E2I System Administration"

# Add custom CSS
admin.site.enable_nav_sidebar = False  # Disable sidebar for cleaner look


# Add custom admin views for additional functionality
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
@csrf_exempt
def generate_api_key_view(request, user_id):
    """Admin view to generate API key for a specific user."""
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST method allowed")
    
    try:
        user = User.objects.get(pk=user_id)
        api_key = user.generate_api_key()
        return JsonResponse({
            'success': True,
            'api_key': api_key,
            'message': f'API key generated for {user.username}'
        })
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# Add the custom view to admin URLs (this would go in your main urls.py)
# from django.urls import path, include
# from e2i_api.apps.common.admin import generate_api_key_view

# admin_patterns = [
#     path('generate_api_key/<uuid:user_id>/', generate_api_key_view, name='generate_api_key'),
# ]