from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from apps.core.admin import get_change_href
from apps.profiles.constants import ContactType
from apps.profiles.models import Profile, User


def get_profile_link(profile: Profile, prelabel=None):
    if not profile:
        return
    return get_change_href(profile, label=f"{prelabel or 'профиль'} - {profile}")


def get_user_link(user: User, label=None):
    if not user:
        return
    return get_change_href(user, label=label or "пользователь")


def get_profile_links_as_common_str(profile: Profile, start_string=None, with_contacts=False):
    links = ""
    if start_string:
        links = start_string + "<br />"

    links += f"> {get_profile_link(profile)}"
    user: User = profile.user
    if user:
        links += f"<br />>  {get_change_href(user, label=f'пользователь - {user}')}"
        if with_contacts:
            links += f"<br />Контакты:"
            for contact in user.contacts.all():
                links += f"<br />- {contact.value}"
            # if log_data.user and log_data.user.has_perm('profiles.change_contact'):
            # email = user.contacts.email
            # phone = user.contacts.phone
            # if phone:
            #     links += f"<br />- {phone}"
            # if email:
            #     links += f"<br />- {email}"

    return links


def get_profile_links(profile: Profile, start_string=None, with_contacts=False):
    links = get_profile_links_as_common_str(profile, start_string, with_contacts)
    return format_html(links)


class UserHasPhoneFilter(SimpleListFilter):
    title = _('Есть ли телефон?')  # a label for our filter
    parameter_name = 'has_phone'  # you can put anything here

    def lookups(self, request, model_admin):
        # This is where you create filter options; we have two:
        return [
            ('yes', _('Да')),
            ('no', _('Нет')),
        ]

    def queryset(self, request, queryset):
        # This is where you process parameters selected by use via filter options:
        with_phone_q = Q(contacts__isnull=False, contacts__type=ContactType.PHONE)
        value = self.value()
        if value == 'yes':
            # Get websites that have at least one page.
            return queryset.filter(with_phone_q)
        elif value == "no":
            # Get websites that don't have any pages.
            return queryset.exclude(with_phone_q)
        return queryset
