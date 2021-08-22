# encoding=utf-8

from django.contrib.auth.models import Group

from apps.core.constants import SYSTEM_SERVICE, SystemUserNames
from apps.profiles.constants import DEFAULT_PASSWORD, ProfileType
from apps.profiles.factories import UserFactory, ProfileFactory

HEAVY = False
DEPENDS_ON = [
    # 'apps.directory.fixtures.region_initial',
]


def load():
    UserFactory(
        username=SystemUserNames.ADMIN,
        name='Site Admin',
        is_superuser=True,
        is_staff=True,
        password=DEFAULT_PASSWORD,
        add_primary_phone=False,
        confirm_email=True,
    )

    system_group, _ = Group.objects.get_or_create(name=SYSTEM_SERVICE)
    system_group.user_set.add(
        UserFactory(
            username=SystemUserNames.SYSTEM,
            password='EnbomeedIkIpekJiacfaryaydBiasJiggOofNaicNeucGueghadAtyogerdibul4',
            email='system@django_example.com',
            add_primary_phone=False,
            confirm_email=True,
            name=SYSTEM_SERVICE,
            profile=ProfileFactory(type=ProfileType.SYSTEM),
        ),
        UserFactory(
            username=SystemUserNames.VOXIMPLANT,
            password='CwkpnBKonLEtBwEsXEmxdyFoUzvGTUpHtZzjVAPaXqPZELsEBEfbmFCVmkMFCPFy',
            email='system+voximplant@django_example.com',
            add_primary_phone=False,
            confirm_email=True,
            name='Voximplant Server',
            profile=ProfileFactory(type=ProfileType.SYSTEM),
        ),
        UserFactory(
            username=SystemUserNames.ONE_C,
            password='ktww7Jb3Q05LhJDOKonwAzDT93eihlIDY3SEOYCumJSKipzBlWeAZeq9pWxBQ78l',
            email='system+1c@django_example.com',
            add_primary_phone=False,
            confirm_email=True,
            name='1C Server',
            profile=ProfileFactory(type=ProfileType.SYSTEM),
        ),
        UserFactory(
            username=SystemUserNames.INTEGRATION,
            password='ksadfftww7Jb3QsdfposhJDOKT93eihl3Sdp-OYCumJSKipzBlWeAZeq9pWxBQ78l',
            email='system+integration@django_example.com',
            add_primary_phone=False,
            confirm_email=True,
            name='Integration',
            profile=ProfileFactory(type=ProfileType.SYSTEM),
        ),
    )
