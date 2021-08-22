from functools import partial

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.checks import BaseModelAdminChecks
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.sites.models import Site
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin

from apps.tools.ordered_admin import MpttAdminMixin


def get_changelist_url(obj):
    return reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist',)


def get_change_url(obj):
    return reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])


def get_change_href(obj, label=None):
    change_url = get_change_url(obj)
    return format_html(f'<a href="{change_url}">{label or obj}</a>')


class SecondaryLinksMixin(object):
    """
    Admin mixin to keep all related links for object in one field

    :Example:
        class SampleModelAdmin(SecondaryLinksMixin, ModelAdmin):
            readonly_fields = ['secondary_links']
            secondary_links_fields = ['reference_link', 'reference_link_2']

            def reference_link(self, obj):
                return sample_admin_url(obj.reference)
    """

    secondary_links_fields = []

    def secondary_links(self, obj):
        links = [getattr(self, method_name)(obj) for method_name in self.secondary_links_fields]
        return '<br/>'.join([link for link in links if link])

    secondary_links.short_description = _('Связанные ссылки')
    secondary_links.allow_tags = True


class DisableDeleteMixin(object):
    """
    Add this class to your ModelAdmin to disable delete action and buttons
    """

    def get_actions(self, request):
        actions = super(DisableDeleteMixin, self).get_actions(request)
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        return False


class EditableCreatedFieldMixin(object):
    if settings.TEST_SERVER:

        def get_fields(self, request, obj=None):
            fields = super(EditableCreatedFieldMixin, self).get_fields(request, obj)
            if obj and 'created' not in fields:
                fields.append('created')
            return fields

        def get_form(self, request, obj=None, **kwargs):
            form = super(EditableCreatedFieldMixin, self).get_form(request, obj, **kwargs)
            if obj:
                form.base_fields['created'].initial = obj.created
            return form

        def save_model(self, request, obj, form, change):
            obj.created = form.cleaned_data['created']
            obj.save()

        def get_readonly_fields(self, request, obj=None):
            fields = super(EditableCreatedFieldMixin, self).get_readonly_fields(request, obj)
            if not obj:
                fields += ('created',)
            return fields


admin.site.unregister(Site)


class ReadOnlyAdminMixin(object):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class SkipRelatedFieldCheck(BaseModelAdminChecks):
    """
    Skip that readonly_fields refers to proper attribute or field.
    Skip that child model relates to parent model.
    """

    def _check_relation(self, *args, **kwargs):
        return []

    def _check_readonly_fields_item(self, *args, **kwargs):
        return []


class FreeRelationInline(ReadOnlyAdminMixin, admin.TabularInline):
    """
    Inline displays the contents of any model in the form of data grid.
    ModelFormSet responsible for custom filter on model.

    :Example:
    class MyFormSet(forms.BaseModelFormSet):
        def __init__(self, instance, queryset=None, **kwargs):

            # instance - object of model in ModelAdmin in which inlines are used
            # queryset - inline.model.objects
            if instance and instance.pk and queryset is not None:
                queryset = queryset.filter(name=instance.some_field)
            super(MyFormSet, self).__init__(instance, queryset, **kwargs)

    class MyInline(CustomTabularInline):
        model = User
        formset = MyFormSet
    """

    checks_class = SkipRelatedFieldCheck
    can_delete = False

    def get_formset(self, request, obj=None, **kwargs):
        return forms.modelformset_factory(
            self.model,
            form=self.form,
            formset=self.formset,
            can_delete=self.can_delete,
            formfield_callback=partial(self.formfield_for_dbfield, request=request),
            max_num=self.max_num,
        )


BUTTON_TEMPLATE = '<a class="button" href="{url}" style="{style}">{title}</a>'


class BaseProcessActionsAdminMixin:
    def get_action_methods(self):
        return {}

    def _get_path_info(self):
        return self.model._meta.app_label, self.model._meta.model_name

    def get_redirect_url__to_referer(self, request: HttpRequest):
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta

        redirect_url = add_preserved_filters(
            {'preserved_filters': preserved_filters, 'opts': opts},
            request.META.get('HTTP_REFERER', '/'),
        )

        return redirect_url

    def process_action(
        self, request, obj_id, action_key, **kwargs,
    ):
        action_methods = self.get_action_methods()
        action = action_methods[action_key]
        obj = self.get_object(request, obj_id)
        return action(request, obj)


class DisplayableAdmin(admin.ModelAdmin):
    list_filter = ('is_displayed',)

    actions = ("make_displayed", "make_hidden")

    def make_displayed(self, request, queryset):
        """
        :type request: django.http.request.HttpRequest
        :type queryset: apps.core.models.DisplayableQuerySet
        :rtype: None
        """
        queryset.mark_displayed()

    make_displayed.short_description = _("Сделать видимыми")

    def make_hidden(self, request, queryset):
        """
        :type request: django.http.request.HttpRequest
        :type queryset: apps.core.models.DisplayableQuerySet
        :rtype: None
        """
        queryset.mark_hidden()

    make_hidden.short_description = _("Сделать скрытыми")


class DisplayableMPTTAdmin(
    DraggableMPTTAdmin, MpttAdminMixin, DisplayableAdmin,
):
    mptt_level_indent = 20
