# encoding=utf-8

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

from functools import update_wrapper
from itertools import chain

from django.db.models import Min
from django.conf import settings
from django.conf.urls import url
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist, ValidationError
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import constants
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, path
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _, ugettext as __

from apps.core.admin import EditableCreatedFieldMixin
from apps.core.decorators import mute_errors

from .exceptions import EmptyReasonError
from .models import ModerationRequest, ModeratedModel
from .forms import RequestAdminForm
from .moderators import SeparatedBaseModerator, register


class MixinRequestInlineSave(object):
    def _get_moderation_object(self, obj):
        if obj.content_object and isinstance(obj.content_object.moderator, SeparatedBaseModerator):
            return obj, 'запрос'

        return obj.content_object, 'объект'

    def moderation_buttons_fn(self, obj):
        # check by empty inline object
        if obj and obj.pk:
            _, mod_obj_caption = self._get_moderation_object(obj)
            prefix = "{}_".format(self.model._meta.app_label)
            if not obj.is_pending:
                reopen_url = reverse('admin:{}reopen'.format(prefix), args=[obj.pk])
                return format_html(
                    '<a href="{}">{}</a>'.format(
                        reopen_url,
                        __('отправить {} на повторную модерацию'.format(mod_obj_caption)),
                    )
                )
            approve_url = reverse('admin:{}approve'.format(prefix), args=[obj.pk])
            if obj.content_object:
                if not obj.content_object.moderator.require_reason:
                    reject_url = reverse('admin:{}reject'.format(prefix), args=[obj.pk])
                    return format_html(
                        '<a href="{}">{}</a> | <a class="reason-link" href="{}">{}</a>'.format(
                            approve_url,
                            __('одобрить {}'.format(mod_obj_caption)),
                            reject_url,
                            __('отклонить {}'.format(mod_obj_caption)),
                        )
                    )
                else:
                    return format_html(
                        '<a href="{}">{}</a>'.format(
                            approve_url, __('одобрить {}'.format(mod_obj_caption))
                        )
                    )

    moderation_buttons_fn.short_description = _('модерация')
    moderation_buttons_fn.admin_order_field = 'is_displayed'
    moderation_buttons_fn.allow_tags = True


class MixinRequestModalSave(object):
    def get_redirect_url(self, request):
        preserved_filters = self.get_preserved_filters(request)
        opts = self.model._meta

        redirect_url = add_preserved_filters(
            {'preserved_filters': preserved_filters, 'opts': opts},
            request.META.get('HTTP_REFERER', '/'),
        )

        return redirect(redirect_url)

    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        Added support for moderation _approve and _reject submit actions.
        """

        opts = self.model._meta

        msg_dict = {'name': force_text(opts.verbose_name), 'obj': force_text(obj)}
        approved = '_approve' in request.POST
        rejected = '_reject' in request.POST
        send_to_moderation = '_send_to_moderation' in request.POST
        if approved or rejected or send_to_moderation:
            # Roughly taken from this clause in ModelAdmin.response_change:
            # >>> if "_continue" in request.POST:
            msg_status = messages.SUCCESS
            try:
                if approved:
                    obj.pre_moderation_validation('approve')
                    msg = __('Объект %(name)s "%(obj)s" одобрен и сохранен') % msg_dict
                    obj.approve(moderated_by=request.user)
                elif rejected:
                    obj.pre_moderation_validation('reject')
                    msg = __('Объект %(name)s "%(obj)s" отклонен и сохранен') % msg_dict
                    obj.reject_action(moderated_by=request.user)
                elif send_to_moderation:
                    obj.pre_moderation_validation('send_to_moderation')
                    msg = (
                        __('Объект %(name)s "%(obj)s" отправлен на модерацию и сохранен') % msg_dict
                    )
                    obj.send_to_moderation(moderated_by=request.user)
            except ValidationError as err:
                msg_status = messages.ERROR
                msg = '; '.join(err.messages)
            except EmptyReasonError:
                msg_status = messages.ERROR
                msg = __('Необходимо указать причину отклонения')

            self.message_user(request, msg, msg_status)

            preserved_filters = self.get_preserved_filters(request)
            redirect_url = add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts}, request.path
            )
            return redirect(redirect_url)
        else:
            return super(MixinRequestModalSave, self).response_change(request, obj)


class RequestInline(GenericTabularInline):
    class Media:
        css = {'all': ['moderation/moderation_admin.css']}
        js = ("moderation/diff.js", "moderation/moderation_admin.js")

    model = ModerationRequest

    readonly_fields = ('status', 'display_changes')
    fields = ('reason',) + readonly_fields

    max_num = 0
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        "Do not allow reason changing after object is approved"
        readonly_fields = super(RequestInline, self).get_readonly_fields(request, obj)
        if (
            obj
            and obj.last_moderation_request_cached
            and not obj.last_moderation_request_cached.is_pending
        ):
            return ('reason',) + readonly_fields
        return readonly_fields


class SeparatedRequestInline(MixinRequestInlineSave, RequestInline):
    readonly_fields = RequestInline.readonly_fields + ('moderation_buttons_fn',)
    fields = RequestInline.fields + ('moderation_buttons_fn',)


class ModeratedAdmin(MixinRequestModalSave, admin.ModelAdmin):
    custom_readonly_fields = ('is_displayed',)
    separated_request_inline_class = SeparatedRequestInline
    request_inline_class = RequestInline

    if not settings.TEST_SERVER:
        custom_readonly_fields += ('moderated_timestamp',)

    def __init__(self, model, admin_site):
        if not issubclass(model, ModeratedModel):
            raise ImproperlyConfigured(
                'ModeratedAdmin can only be used with subclasses of ModeratedModel'
            )
        super(ModeratedAdmin, self).__init__(model, admin_site)

    def get_queryset(self, request):
        queryset = self.model.default_manager.all()
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_object(self, request, object_id, from_field=None):
        model = self.model
        try:
            object_id = model._meta.pk.to_python(object_id)
            return model.default_manager.select_for_update(nowait=True).get(pk=object_id)
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(ModeratedAdmin, self).get_readonly_fields(request, obj)
        return tuple(readonly_fields) + self.custom_readonly_fields

    def save_model(self, request, obj, form, change):
        obj.save(changed_by=request.user)

    def get_inline_instances(self, request, obj=None):
        """
        Inject RequestInline into ModeratedAdmin inheritors,
        so ModerationRequest.reason field is displayed in instance edit view
        """
        inline_instances = super(ModeratedAdmin, self).get_inline_instances(request, obj)

        if obj:
            if isinstance(obj.moderator, SeparatedBaseModerator):
                moderated_inline = self.separated_request_inline_class
            else:
                moderated_inline = self.request_inline_class

            inline_instances.append(moderated_inline(self.model, self.admin_site))

        return inline_instances

    def moderation_status(self, obj):
        return obj.moderation_request_status

    moderation_status.short_description = _('статус модерации')


class ContentTypeFilter(admin.SimpleListFilter):
    title = _('тип объекта')

    parameter_name = 'content_type'
    _new_profile = 'new_profile'
    _partial_review = 'partial_review'

    def lookups(self, request, model_admin):
        return sorted(
            chain(
                (
                    (c.pk, c.name.capitalize())
                    for c in ContentType.objects.get_for_models(
                        *register.moderators.keys()
                    ).values()
                ),
                [
                    (self._new_profile, _('New profile')),
                    (self._partial_review, _('Partial review')),
                ],
            ),
            key=lambda x: x[1],
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == self._new_profile:
            profile_type = ContentType.objects.get(app_label='profiles', model='profile')
            return queryset.filter(
                pk__in=queryset.filter(content_type=profile_type)
                .order_by('object_id')
                .values('object_id')
                .annotate(min_id=Min('id'))
                .values('min_id')
            )

        elif value == self._partial_review:
            order_review = ContentType.objects.get(app_label='orders', model='review')
            review_model = order_review.model_class()

            return queryset.filter(
                content_type=order_review,
                object_id__in=review_model.default_manager.filter(is_full_review=False)
                .exclude(details='')
                .values_list('id', flat=True),
            )

        elif value:
            return queryset.filter(content_type__pk=value)

        return queryset


class ModerationStatusFilter(admin.SimpleListFilter):
    title = _('статус модерации')
    parameter_name = 'moderation_status'

    def lookups(self, request, model_admin):
        return (('moderated', __('Проверен')), ('not_moderated', __('Не проверен')))

    def queryset(self, request, queryset):
        if self.value() == 'moderated':
            return queryset.filter(moderated_timestamp__isnull=False)
        if self.value() == 'not_moderated':
            return queryset.filter(moderated_timestamp__isnull=True)
        return queryset


class RequestStatusFilter(admin.SimpleListFilter):
    """
    Custom choices filter for specifying a default selected option,
    other than 'All' that Django provides
    """

    title = _('статус')
    parameter_name = 'status'
    default = ModerationRequest.STATUS_PENDING
    _all = 'all'

    def lookups(self, request, model_admin):
        return ((self._all, __('All')),) + model_admin.model.STATUS_CHOICES

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            is_default = self.value() is None and lookup == self.default
            yield {
                'selected': is_default or self.value() == force_text(lookup),
                'query_string': cl.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if not self.value():
            return queryset.filter(status=self.default)
        if self.value() == self._all:
            return queryset
        else:
            return queryset.filter(status=self.value())


@admin.register(ModerationRequest)
class ModerationRequestAdmin(
    MixinRequestInlineSave, MixinRequestModalSave, EditableCreatedFieldMixin, admin.ModelAdmin
):
    list_display = (
        'id',
        'content_object_display',
        'content_type',
        'moderation_buttons_fn',
        'status',
        'moderated_by',
        'moderated_timestamp',
        'extra_data_field',
    )
    actions = ('approve_queryset', 'reopen_queryset')
    exclude = ('watched_changes', 'object_id', 'content_type', 'section')
    list_filter = ('section', RequestStatusFilter, ContentTypeFilter)
    search_fields = (
        'moderated_by__username',
        '=object_id',
        'changed_by__username',
        '=changed_by__contacts__value',
    )

    readonly_fields = [
        'content_object_display',
        'display_changes',
        'object_id',
        'content_type',
        'moderated_by',
        'changed_by',
    ]
    ordering = ('id',)

    if settings.TEST_SERVER:
        form = RequestAdminForm
    else:
        readonly_fields = ['status'] + readonly_fields + ['moderated_timestamp', 'created']

    def get_readonly_fields(self, request, obj=None):
        fields = super(ModerationRequestAdmin, self).get_readonly_fields(request, obj)[:]
        if obj and obj.content_object:
            moderator = obj.content_object.moderator
            fields.extend([f for f in moderator.extra_admin_fields if not f in fields])
        return fields

    def get_search_results(self, request, queryset, search_term):
        queryset, _ = super(ModerationRequestAdmin, self).get_search_results(
            request, queryset, search_term
        )
        return queryset, True

    def action_view(self, request, pk, action_name, action_caption):
        obj = get_object_or_404(self.model, pk=pk)
        try:
            mod_obj, mod_obj_caption = self._get_moderation_object(obj)
            mod_obj.pre_moderation_validation(action_name)
            getattr(mod_obj, action_name)(moderated_by=request.user)
            self.message_user(request, __('{} {} {}').format(mod_obj_caption, obj, action_caption))
        except ValidationError as err:
            self.message_user(
                request, __('{} {}').format(obj, '; '.join(err.messages)), level=constants.ERROR
            )
        except EmptyReasonError:
            self.message_user(
                request, __('Необходимо указать причину отклонения'), level=constants.ERROR
            )
        return self.get_redirect_url(request)

    def approve_view(self, request, pk):
        return self.action_view(request, pk, 'approve', 'одобрен')

    def reject_view(self, request, pk):
        return self.action_view(request, pk, 'reject', 'отклонен')

    def reopen_view(self, request, pk):
        return self.action_view(request, pk, 'send_to_moderation', 'отправлен на модерацию')

    def action_queryset(self, request, queryset, action_name, action_caption):
        counter = {}
        for obj in queryset:
            if (
                action_name in ['approve', 'reject']
                and obj.is_pending
                or action_name == 'send_to_moderation'
                and not obj.is_pending
            ):
                mod_obj, mod_obj_caption = self._get_moderation_object(obj)
                counter.setdefault(mod_obj_caption, 0)
                counter[mod_obj_caption] += 1
                getattr(obj, action_name)(moderated_by=request.user)

        for key, val in counter.iteritems():
            text_message = __('{} {}ов'.format(action_caption, key))
            self.message_user(request, '{}: {}'.format(text_message, val))

    def approve_queryset(self, request, queryset):
        self.action_queryset(request, queryset, 'approve', 'Одобрено')

    approve_queryset.short_description = __('одобрить')

    def reopen_queryset(self, request, queryset):
        self.action_queryset(request, queryset, 'send_to_moderation', 'Отправлено на модерацию')

    reopen_queryset.short_description = __('отправить на повторную модерацию')

    @mute_errors
    def extra_data_field(self, obj):
        profiles_picture = ContentType.objects.get(app_label='profiles', model='picture')
        contractor_specification = ContentType.objects.get(
            app_label='profiles', model='contractorspecification'
        )
        if obj.content_type.model == profiles_picture.model:
            if obj.content_object and obj.content_object.cropped_file:
                from sorl.thumbnail import get_thumbnail

                legal_form = ''
                previous_picture = ''
                try:
                    contractor = obj.content_object.profile.contractor
                except ObjectDoesNotExist:
                    contractor = None

                if obj.content_object.profile.is_contractor and contractor:
                    legal_form = 'Организационно-правовая форма исполнителя: {}</br></br>'.format(
                        contractor.legal_form.title
                    )
                    if contractor.is_documents_confirmed and obj.content_object.profile.picture:
                        picture = get_thumbnail(
                            obj.content_object.profile.picture.cropped_file, '150x150'
                        )
                        previous_picture = (
                            '</br></br>Старое изображение профиля:'
                            '</br><img src="{}"></br>Данные подтверждены'
                        ).format(picture.url)
                image = get_thumbnail(obj.content_object.cropped_file, '150x150')
                return 'Имя профиля: {}</br>Тип профиля: {}</br></br>{}<img src="{}">{}'.format(
                    obj.content_object.profile.full_name,
                    obj.content_object.profile.get_type_display(),
                    legal_form,
                    image.url,
                    previous_picture,
                )
        elif obj.content_type.model == contractor_specification.model:
            return 'Категория: {}</br>Описание: {}'.format(
                obj.content_object.category.title, obj.watched_changes['details'][1]
            )
        return None

    extra_data_field.allow_tags = True
    extra_data_field.short_description = __('дополнительные данные')

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            return update_wrapper(wrapper, view)

        prefix = "{}_".format(self.model._meta.app_label)
        return [
            path(
                '<path:object_id>/approve/',
                wrap(self.approve_view),
                name="{}approve".format(prefix),
            ),
            path(
                '<path:object_id>/reject/', wrap(self.reject_view), name="{}reject".format(prefix)
            ),
            path(
                '<path:object_id>/reopen/', wrap(self.reopen_view), name="{}reopen".format(prefix)
            ),
        ] + super(ModerationRequestAdmin, self).get_urls()
