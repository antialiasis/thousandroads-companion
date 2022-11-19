from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from forum.models import User, Member, Fic, Genre, Review
from awards.models import verify_current


class ForumUserAdmin(UserAdmin):
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
        super(ForumUserAdmin, self).save_model(request, obj, form, change)


class MemberAdmin(admin.ModelAdmin):
    def save_form(self, request, form, change):
        if change and 'user_id' in form.changed_data:
            self.old_member_id = request.resolver_match.args[0]
        return super(MemberAdmin, self).save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        super(MemberAdmin, self).save_model(request, obj, form, change)
        print(obj.user_id, form.instance.user_id, self.old_member_id)
        if change and 'user_id' in form.changed_data:
            old_instance = Member.objects.get(user_id=self.old_member_id)
            old_instance.nominations.update(nominee_id=obj)
            old_instance.nominations_by.update(member_id=obj)
            old_instance.votes.update(member=obj)
            old_instance.delete()


admin.site.register(User, ForumUserAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(Fic)
admin.site.register(Genre)
admin.site.register(Review)
