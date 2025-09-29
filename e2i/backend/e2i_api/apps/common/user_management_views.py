# e2i_api/apps/common/user_management_views.py

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone
from .auth import admin_required, _json_error, get_current_user

logger = logging.getLogger(__name__)
User = get_user_model()


@admin_required
def user_list_view(request):
    """
    Get list of all users (Admin only)
    GET /users/
    """
    if request.method != 'GET':
        return _json_error("METHOD_NOT_ALLOWED", "Only GET allowed", 405)

    try:
        users = User.objects.all().order_by('username')
        
        users_data = []
        for user in users:
            # Get last login from the most recent session
            last_login = None
            try:
                from .models import UserSession
                last_session = UserSession.objects.filter(
                    user=user, 
                    is_active=False
                ).order_by('-last_accessed').first()
                if last_session:
                    last_login = last_session.last_accessed
            except Exception as e:
                logger.warning(f"Could not get last login for user {user.username}: {e}")

            users_data.append({
                "id": str(user.id),
                "username": user.username,
                "email": user.email or "",
                "role": user.role,
                "active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "last_login": last_login.isoformat() if last_login else None,
                "has_api_key": bool(user.api_key)
            })

        return JsonResponse({
            "success": True,
            "users": users_data,
            "total": len(users_data)
        })

    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return _json_error("INTERNAL_ERROR", "Failed to fetch users", 500)


@csrf_exempt
@admin_required
def user_create_view(request):
    """
    Create a new user (Admin only)
    POST /users/
    Body: {"username": "user", "email": "email", "role": "user", "password": "pass"}
    """
    if request.method != 'POST':
        return _json_error("METHOD_NOT_ALLOWED", "Only POST allowed", 405)

    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        role = data.get('role', 'user')
        password = data.get('password')

        if not username or not password:
            return _json_error("BAD_REQUEST", "Username and password are required")

        if role not in ['admin', 'user']:
            return _json_error("BAD_REQUEST", "Role must be 'admin' or 'user'")

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return _json_error("USER_EXISTS", "Username already exists", 409)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role
        )

        return JsonResponse({
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email or "",
                "role": user.role,
                "active": user.is_active
            }
        }, status=201)

    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return _json_error("INTERNAL_ERROR", "Failed to create user", 500)


@csrf_exempt
@admin_required
def user_delete_view(request, user_id):
    """
    Delete a user (Admin only)
    DELETE /users/<user_id>/
    """
    if request.method != 'DELETE':
        return _json_error("METHOD_NOT_ALLOWED", "Only DELETE allowed", 405)

    try:
        current_user = get_current_user(request)
        
        # Prevent admin from deleting themselves
        if str(current_user.id) == str(user_id):
            return _json_error("BAD_REQUEST", "Cannot delete your own account", 400)

        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()

        return JsonResponse({
            "success": True,
            "message": f"User '{username}' deleted successfully"
        })

    except User.DoesNotExist:
        return _json_error("USER_NOT_FOUND", "User not found", 404)
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return _json_error("INTERNAL_ERROR", "Failed to delete user", 500)


@csrf_exempt
@admin_required
def user_toggle_status_view(request, user_id):
    """
    Toggle user active status (Admin only)
    POST /users/<user_id>/toggle-status/
    """
    if request.method != 'POST':
        return _json_error("METHOD_NOT_ALLOWED", "Only POST allowed", 405)

    try:
        current_user = get_current_user(request)
        
        # Prevent admin from deactivating themselves
        if str(current_user.id) == str(user_id):
            return _json_error("BAD_REQUEST", "Cannot deactivate your own account", 400)

        user = User.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()

        status = "activated" if user.is_active else "deactivated"
        return JsonResponse({
            "success": True,
            "message": f"User '{user.username}' {status} successfully",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "active": user.is_active
            }
        })

    except User.DoesNotExist:
        return _json_error("USER_NOT_FOUND", "User not found", 404)
    except Exception as e:
        logger.error(f"Error toggling user status: {e}")
        return _json_error("INTERNAL_ERROR", "Failed to update user status", 500)


@csrf_exempt
@admin_required
def user_update_view(request, user_id):
    """
    Update user information (Admin only)
    PUT /users/<user_id>/
    Body: {"email": "new@email.com", "role": "admin"}
    """
    if request.method != 'PUT':
        return _json_error("METHOD_NOT_ALLOWED", "Only PUT allowed", 405)

    try:
        data = json.loads(request.body)
        user = User.objects.get(id=user_id)

        # Update fields if provided
        if 'email' in data:
            user.email = data['email']
        
        if 'role' in data:
            if data['role'] not in ['admin', 'user']:
                return _json_error("BAD_REQUEST", "Role must be 'admin' or 'user'")
            user.role = data['role']

        user.save()

        return JsonResponse({
            "success": True,
            "message": "User updated successfully",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email or "",
                "role": user.role,
                "active": user.is_active
            }
        })

    except json.JSONDecodeError:
        return _json_error("BAD_REQUEST", "Invalid JSON body")
    except User.DoesNotExist:
        return _json_error("USER_NOT_FOUND", "User not found", 404)
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return _json_error("INTERNAL_ERROR", "Failed to update user", 500)


