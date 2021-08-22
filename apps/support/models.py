from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.db import models
from django.template.defaultfilters import striptags, truncatewords
from django.utils.translation import ugettext_lazy as _

from apps.core.models import DisplayableModel, TimeStampIndexedModel
from apps.profiles.models import User


class FrequentQuestion(DisplayableModel, TimeStampIndexedModel):
    question = RichTextField(_('Вопрос'), help_text=_(''))
    answer = RichTextField(_('Ответ'), help_text=_(''))

    def __str__(self):
        return truncatewords(striptags(self.question), 5)

    class Meta:
        verbose_name = _('Часто задаваемый вопрос')
        verbose_name_plural = _('Часто задаваемые вопросы')


class SupportRequest(TimeStampIndexedModel):
    email = models.EmailField(_("Email"), max_length=300, null=True, blank=True)
    phone = models.CharField(_("Телефон"), max_length=300, null=True, blank=True)
    text = models.TextField(_("Текст"))
    is_processed = models.BooleanField(_("Обработано?"), default=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING)

    class Meta:
        verbose_name = _('Обращение в саппорт')
        verbose_name_plural = _('Обращения в саппорт')

    def __str__(self):
        return f"От: {self.email or self.phone}. Текст: {truncatewords(self.text, 5)}"

    def clean(self):
        if not self.phone and not self.email:
            raise ValidationError(_('phone on email must be filled'))

    def mark_processed(self, save=True):
        self.is_processed = True
        if save:
            self.save()
