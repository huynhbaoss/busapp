from rest_framework import permissions
from .models import User
from django.contrib.auth.models import Group


class CommentOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, comment):
        return request.user and request.user == comment.user


class ReviewOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, review):
        return request.user and request.user == review.user


class IsUserorTransportCompany(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return request.user.groups.filter(
            name='Seller').exists() and request.user.is_verified is True or request.user.is_staff is True

    def has_object_permission(self, request, view, shop):
        return request.user and request.user == shop.user


class IsSuperAdminOrEmployee(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        # return request.user.is_staff is True
        return request.user.is_staff is True or User.objects.filter(pk=request.user.id, role='E').exists()
