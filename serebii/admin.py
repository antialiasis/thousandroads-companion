from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from serebii.models import User, Member, Fic

class SerebiiUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Member info'), {'fields': ('member', 'verified')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'member', 'email', 'is_staff', 'verified')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'verified', 'groups')

admin.site.register(User, SerebiiUserAdmin)
admin.site.register(Member)
admin.site.register(Fic)