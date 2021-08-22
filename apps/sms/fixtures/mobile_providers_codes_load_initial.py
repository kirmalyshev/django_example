# encoding=utf-8

from __future__ import print_function, unicode_literals

from apps.sms import factories
from apps.sms.constants import FAKE_OPERATOR_CODE

SKIP_FOR_TEST = True
HEAVY = False


def load():
    F = factories.MobileCodeFactory
    F(code='139', provider='Для тестовых аккаунтов. Не удалять!')

    F(code='900', provider='«Мотив»')
    F(
        code='901',
        provider='«ЕТК», «Билайн», «Ростелеком», «МССС» (Ставрополь), «Скай Линк», «Utel», «Байкалвестком», МТТ, «КБСС» (Нальчик), «СТЕЛС», Сотовая связь Калмыкии',
    )
    F(
        code='902',
        provider='«СМАРТС», «ЕТК», «НТК» (Приморье), «АКОС», «Ростелеком», «Оренбург GSM», «Теле2», «НСС» (Н.Новгород), «Мотив», «Билайн», «Байкалвестком», «Utel»',
    )
    F(code='903', provider='«Билайн»')
    F(
        code='904',
        provider='«СМАРТС», «ЕТК», «НТК» (Приморье), «Теле2», «НСС» (Н.Новгород), «Мотив», «Байкалвестком», «Utel»',
    )
    F(code='905', provider='«Билайн»')
    F(code='906', provider='«Билайн»')

    F(
        code='908',
        provider='«СМАРТС», «ЕТК», «НТК» (Приморье), «Теле2», «Ростелеком», «Оренбург GSM», «НСС» (Н.Новгород), «Мотив», «Билайн», «Байкалвестком», «Utel»',
    )
    F(code='909', provider='«Билайн»')
    F(code='910', provider='«МТС»')
    F(code='911', provider='«МТС»')
    F(code='912', provider='«МТС»')
    F(code='913', provider='«МТС»')
    F(code='914', provider='«МТС»')
    F(code='915', provider='«МТС»')
    F(code='916', provider='«МТС»')
    F(code='917', provider='«МТС»')
    F(code='918', provider='«МТС»')
    F(code='919', provider='«МТС»')

    F(code='920', provider='«Мегафон»')
    F(code='921', provider='«Мегафон»')
    F(code='922', provider='«Мегафон»')
    F(code='923', provider='«Мегафон»')
    F(code='924', provider='«Мегафон»')
    F(code='925', provider='«Мегафон»')
    F(code='926', provider='«Мегафон»')
    F(code='927', provider='«Мегафон»')
    F(code='928', provider='«Мегафон»')
    F(code='929', provider='«Мегафон»')
    F(code='930', provider='«Мегафон»')
    F(code='931', provider='«Мегафон»')
    F(code='932', provider='«Мегафон»')
    F(code='933', provider='«Мегафон»')
    F(code='934', provider='«Мегафон»')
    F(code='936', provider='«Мегафон»')
    F(code='937', provider='«Мегафон»')
    F(code='938', provider='«Мегафон»')

    F(
        code='950',
        provider='«СМАРТС», «ЕТК», «АКОС», «Теле2», «Ростелеком», «Оренбург GSM», «Мотив», «Байкалвестком», «НСС» (Н.Новгород), «Utel»',
    )
    F(
        code='951',
        provider='«НТК» (Приморье), «Теле2», «Ростелеком», «Оренбург GSM», «ЕТК», «НСС» (Н.Новгород), «СМАРТС», «Utel»',
    )
    F(
        code='952',
        provider='«АКОС», «Теле2», «Байкалвестком», «ЕТК», «Мотив», «НСС» (Н.Новгород), «Кодотел», «Utel»',
    )
    F(
        code='953',
        provider='«ЕТК», «Оренбург GSM», «НТК» (Приморье), «Теле2», «Мотив», «НСС» (Н.Новгород), «Кодотел», «Utel»',
    )

    F(code='958', provider='«Ростелеком»')
    F(code='960', provider='«Билайн»')
    F(code='961', provider='«Билайн»')
    F(code='962', provider='«Билайн»')
    F(code='965', provider='«Билайн»')
    F(code='966', provider='«Билайн»')
    F(code='964', provider='«Билайн»')
    F(code='963', provider='«Билайн»')
    F(code='967', provider='«Билайн»')
    F(code='968', provider='«Билайн»')

    F(code='977', provider='Теле2')
    F(code='978', provider='МТС')

    F(code='980', provider='«МТС»')
    F(code='981', provider='«МТС»')
    F(code='982', provider='«МТС»')
    F(code='983', provider='«МТС»')
    F(code='984', provider='«МТС»')
    F(code='985', provider='«МТС»')
    F(code='987', provider='«МТС»')
    F(code='988', provider='«МТС»')
    F(code='989', provider='«МТС»')

    F(code='991', provider='«Теле2»')
    F(code='992', provider='«Теле2»')
    F(code='993', provider='«Теле2»')
    F(code='994', provider='«Теле2»')
    F(code='995', provider='«Теле2»')
    F(code='996', provider='«Теле2»')
    F(code='997', provider='«Мегафон»')
    F(code='999', provider='«Yota»')

    F(code=FAKE_OPERATOR_CODE, provider='Для тестовых пользователей')


def TestMobileProvidersCodeLoad(F=factories.MobileCodeFactory):
    F(code='139', provider='Для тестовых аккаунтов. Не удалять!')


def test_load():
    TestMobileProvidersCodeLoad()
