import copy

from functools import update_wrapper

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.contrib import admin


class MpttAdminMixin(object):
    actions = [
        'rebuild_mptt_action',
    ]

    def rebuild_mptt_action(self, queryset, request):
        self.model._tree_manager.rebuild()

    rebuild_mptt_action.short_description = _('Обновить mptt дерево')


class OrderedModelAdmin(MpttAdminMixin, admin.ModelAdmin):
    show_all = True
    ordering = ('compose_position',)

    buttons_template = 'ordered_model/admin/order_controls.html'

    def get_fieldsets(self, request, obj=None):
        result = copy.copy(super(OrderedModelAdmin, self).get_fieldsets(request, obj=None))
        try:
            if obj:
                result[0][1]['fields'].remove('parent')
        except ValueError:
            pass
        return result

    def get_model_info(self):
        return dict(app=self.model._meta.app_label, model=self.model._meta.model_name)

    def get_urls(self):
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            return update_wrapper(wrapper, view)

        pattern_args = [
            url(
                r'^(.+)/move-(up)/$',
                wrap(self.move_view),
                name='{app}_{model}_order_up'.format(**self.get_model_info()),
            ),
            url(
                r'^(.+)/move-(down)/$',
                wrap(self.move_view),
                name='{app}_{model}_order_down'.format(**self.get_model_info()),
            ),
        ]
        try:
            from django.conf.urls import patterns

            return patterns('', *pattern_args) + super(OrderedModelAdmin, self).get_urls()
        except ImportError:
            return pattern_args + super(OrderedModelAdmin, self).get_urls()

    def move_view(self, request, object_id, direction):
        obj = get_object_or_404(self.model, pk=object_id)
        if direction == 'up':
            obj.up()
        else:
            obj.down()

        return HttpResponseRedirect('../../')

    def move_up_down_links(self, obj):
        return render_to_string(
            self.buttons_template,
            {
                'app_label': self.model._meta.app_label,
                'module_name': self.model._meta.model_name,
                'object_id': obj.id,
                'urls': {
                    'up': reverse(
                        "admin:{app}_{model}_order_up".format(**self.get_model_info()),
                        args=[obj.id, 'up'],
                    ),
                    'down': reverse(
                        "admin:{app}_{model}_order_down".format(**self.get_model_info()),
                        args=[obj.id, 'down'],
                    ),
                },
            },
        )

    move_up_down_links.allow_tags = True
    move_up_down_links.short_description = _(u'Перемещение')
