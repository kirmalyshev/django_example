from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from apps.core.constants import CREATED, MODIFIED
from apps.support.models import FrequentQuestion, SupportRequest


@admin.register(FrequentQuestion)
class FrequentQuestionAdmin(admin.ModelAdmin):
    search_fields = ('question', 'answer')
    list_display = ('id', 'question', 'answer')
    list_display_links = (
        'id',
        'question',
    )


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin,):
    date_hierarchy = CREATED
    search_fields = ('email', 'phone', 'text')
    list_filter = ('is_processed',)
    list_display = (
        'id',
        'email',
        'phone',
        'user',
        'text',
        'is_processed',
        CREATED,
        MODIFIED,
    )
    readonly_fields = (
        'id',
        'email',
        'phone',
        'user',
        'text',
        CREATED,
        MODIFIED,
    )
    list_display_links = (
        'id',
        'email',
    )
    fieldsets = (
        (None, {'fields': ('id', 'email', 'phone', 'user', 'text', 'is_processed',)},),
        (_('Внутренняя информация'), {'fields': (CREATED, MODIFIED,)},),
    )

    def has_delete_permission(self, request, obj=None):
        return False
