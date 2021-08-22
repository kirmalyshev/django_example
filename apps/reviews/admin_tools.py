from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _


class HasTextFilter(SimpleListFilter):
    title = _('Есть ли текст?')  # a label for our filter
    parameter_name = 'has_text'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        no_text_q = Q(Q(text__isnull=True) | Q(text=''))
        if self.value() == 'yes':
            # Get websites that have at least one page.
            return queryset.exclude(no_text_q)
        if self.value():
            # Get websites that don't have any pages.
            return queryset.filter(no_text_q)
