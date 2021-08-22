import random

from apps.clinics.factories import ServiceFactory, SubsidiaryFactory, ServicePriceFactory
from apps.clinics.fixtures.subsidiaries_initial import subsidiary_titles
from apps.clinics.models import Service
from apps.core.constants import EMPTY_STR

DEPENDS_ON = ['apps.clinics.fixtures.subsidiaries_initial']


def _get_random_subsidiaries():
    return [SubsidiaryFactory(title=random.choice(subsidiary_titles))]


def load():
    F = ServiceFactory
    Service._set_mptt_updates_enabled(False)
    root_ginecology = F(
        title='Гинекология',
        description=EMPTY_STR,
        subsidiaries=_get_random_subsidiaries(),
        parent=None,
        is_visible_for_appointments=True,
    )
    root_urology = F(
        title='Урология',
        description=EMPTY_STR,
        subsidiaries=_get_random_subsidiaries(),
        parent=None,
        is_visible_for_appointments=True,
    )
    root_analysis = F(
        title='Анализы',
        description=EMPTY_STR,
        subsidiaries=_get_random_subsidiaries(),
        parent=None,
        is_visible_for_appointments=True,
    )

    analysis_1 = F(
        title='Кровь',
        description=EMPTY_STR,
        parent=root_analysis,
        subsidiaries=root_analysis.subsidiaries.all(),
    )
    analysis_ultrasound = F(
        title='УЗИ',
        description=EMPTY_STR,
        parent=root_analysis,
        subsidiaries=root_analysis.subsidiaries.all(),
    )
    analysis_3 = F(
        title='Рентген',
        description=EMPTY_STR,
        parent=root_analysis,
        subsidiaries=root_analysis.subsidiaries.all(),
    )

    root_stomatology = F(
        title='Стоматология',
        description="Стоматология — одно из основных направлений деятельности нашего медицинского центра. На протяжении уже 20 лет наши врачи занимаются решением самых разнообразных задач, связанных со здоровьем зубов.",
        parent=None,
        subsidiaries=_get_random_subsidiaries(),
        is_visible_for_appointments=True,
    )

    stomatolog_1 = F(
        title='Стоматолог-ортопед',
        parent=root_stomatology,
        subsidiaries=root_stomatology.subsidiaries.all(),
    )
    title_prices = (
        ("Консультация стоматолога-ортопеда", "220 руб"),
        (
            "Консультация ортопеда-стоматолога с составлением плана ортопедического лечения с использованием КТ",
            "550 руб",
        ),
        ("Повторный приём стоматолога-ортопеда", "от 1000 руб"),
        ("Металлокерамическая коронка", "от 8000 руб"),
    )
    for i, (title, price) in enumerate(title_prices):
        ServicePriceFactory(service=stomatolog_1, title=title, price=price, priority=i)

    Service._set_mptt_updates_enabled(True)
    Service.tree_manager.rebuild()
