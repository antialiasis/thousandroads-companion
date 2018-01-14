from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from serebii.models import User, Member, Fic
from awards.models import verify_current


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

    def save_model(self, request, obj, form, change):
        if change and obj.verified and 'verified' in form.changed_data:
            # We've verified the user - verify their current nominations/votes
            verify_current(obj.member)
        super(SerebiiUserAdmin, self).save_model(request, obj, form, change)

admin.site.register(User, SerebiiUserAdmin)
admin.site.register(Member)
admin.site.register(Fic)
