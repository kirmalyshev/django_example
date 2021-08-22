from ckeditor.fields import RichTextField
from django.conf.locale.ru.formats import DATE_INPUT_FORMATS
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, IntegrityError
from django.db.models.fields.json import JSONField
from django.utils import formats
from django.utils.translation import ugettext as _
from model_utils.models import TimeStampedModel, StatusModel
from mptt.fields import TreeForeignKey
from mptt.managers import TreeManager
from mptt.models import MPTTModel
from slugify import slugify
from typing import Optional

from apps.clinics.constants import DoctorStatus, DOCTOR_STR
from apps.clinics.managers import (
    PromotionQuerySet,
    SubsidiaryImageManager,
    ServiceManager,
    DoctorManager,
    DoctorAllManager,
)
from apps.core.models import (
    ClinicSoftDeletableModel,
    TimeStampIndexedModel,
    DeletableDisplayable,
    DisplayableModel,
    DisplayableMPTTModel,
    DisplayableManager,
)
from apps.core.utils import validate_image_max_size, human_dt
from apps.profiles.models import User


class ClinicImage(TimeStampIndexedModel):
    image = models.ImageField(
        _('картинка'), upload_to='subsidiary_images/', validators=[validate_image_max_size],
    )
    priority = models.PositiveSmallIntegerField(
        _('Приоритет показа'),
        help_text='чем выше значение - тем выше в выдаче',
        default=0,
        db_index=True,
    )

    class Meta:
        verbose_name = _('Фото клиники')
        verbose_name_plural = _('Фото клиники')
        ordering = ('-priority',)


class Subsidiary(DeletableDisplayable, TimeStampIndexedModel):
    title = models.CharField(_('название филиала'), max_length=150)
    description = models.TextField(_('описание'), null=True, blank=True)

    address = models.CharField(_('адрес'), max_length=500)
    short_address = models.CharField(_('короткий адрес'), max_length=100)
    latitude = models.DecimalField(
        _('широта'), null=True, blank=True, max_digits=9, decimal_places=6
    )
    longitude = models.DecimalField(
        _('долгота'), null=True, blank=True, max_digits=9, decimal_places=6
    )
    integration_data = JSONField(verbose_name=_('Данные об интеграции'), default=dict, blank=True,)

    @property
    def primary_image(self):
        image = self.images.all().only_primary().first()
        return image and image.picture

    class Meta:
        verbose_name = _('Филиал')
        verbose_name_plural = _('Филиалы')

    def __str__(self):
        return f'{self.title}'


class SubsidiaryImage(models.Model):
    subsidiary = models.ForeignKey(
        Subsidiary,
        related_name='images',
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name=_('филиал'),
    )
    picture = models.ImageField(
        _('картинка'), upload_to='subsidiary_images/', validators=[validate_image_max_size],
    )
    is_primary = models.BooleanField(verbose_name=_('основное?'), default=False)
    priority = models.PositiveSmallIntegerField(
        _('Приоритет показа'),
        help_text='чем выше значение - тем выше в выдаче',
        default=0,
        db_index=True,
    )
    objects = SubsidiaryImageManager()

    class Meta:
        verbose_name = _('Фото филиала')
        verbose_name_plural = _('Фото филиалов')
        ordering = ('is_primary', '-priority')

    def clean(self):
        if self.is_primary:
            existing_images = SubsidiaryImage.objects.filter(
                subsidiary=self.subsidiary, is_primary=True
            )
            if self.pk:
                existing_images = existing_images.exclude(pk=self.pk)
            if existing_images.exists():
                raise ValidationError(_('У филиала уже есть основное фото'))

    def save(self, *args, **kwargs):
        if self.is_primary:
            self.subsidiary.images.unset_primary(exclude_pk=self.pk)

        self.full_clean()
        super(SubsidiaryImage, self).save(*args, **kwargs)


class SubsidiaryContact(TimeStampIndexedModel):
    subsidiary = models.ForeignKey(
        Subsidiary,
        verbose_name=_('филиал'),
        related_name='contacts',
        on_delete=models.CASCADE,
        db_index=True,
    )
    title = models.CharField(_('название'), max_length=50, help_text='Телефон/email/факс')
    value = models.CharField(
        _('значение'),
        max_length=100,
        help_text='+7999-888-77-66/admin@clinic.ru/+7111-222-333-44-55',
    )
    ordering_number = models.PositiveSmallIntegerField(
        _('Приоритет показа'), help_text='отображение по порядку - от 1 до 100500', default=0
    )

    class Meta:
        verbose_name = _('Контакт филиала')
        verbose_name_plural = _('Контакты филиалов')
        ordering = ('-ordering_number',)


class SubsidiaryWorkday(TimeStampIndexedModel):
    subsidiary = models.ForeignKey(
        Subsidiary,
        verbose_name=_('филиал'),
        related_name='workdays',
        on_delete=models.CASCADE,
        db_index=True,
    )
    weekday = models.CharField(
        _('день недели'),
        max_length=50,
        help_text='Понедельник/Вторник... Или "ежедневно", "выходные"',
    )
    value = models.CharField(
        _('значение'),
        max_length=50,
        help_text='+7999-888-77-66/admin@clinic.ru/+7111-222-333-44-55',
    )
    ordering_number = models.PositiveSmallIntegerField(
        _('Порядок показа'), help_text='отображение по порядку - от 1 до 100500', default=1
    )

    class Meta:
        verbose_name = _('рабочий день филиала')
        verbose_name_plural = _('рабочие дни филиалов')
        ordering = ('-ordering_number',)


class ServiceToSubsidiary(models.Model):
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.DO_NOTHING)

    def save(self, *args, **kwargs):
        if ServiceToSubsidiary.objects.filter(
            service=self.service, subsidiary=self.subsidiary
        ).exists():
            raise IntegrityError(
                f'Service id {self.service_id} already exists '
                f'for subsidiary id={self.subsidiary_id}'
            )
        super(ServiceToSubsidiary, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('связь услуги с филиалом')
        verbose_name_plural = _('связи услуг с филиалами')


class Service(DisplayableMPTTModel, TimeStampIndexedModel):
    SLUG_SEPARATOR = '_'
    title = models.CharField(_('название'), max_length=100)
    slug = models.SlugField(_('URL'), max_length=255, unique=True, blank=True, null=True)
    subsidiaries = models.ManyToManyField(Subsidiary, through=ServiceToSubsidiary)
    description = models.TextField(_('описание'), null=True, blank=True)
    parent = TreeForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.DO_NOTHING,
    )
    is_visible_for_appointments = models.BooleanField(
        _('Видна ли услуга во флоу записи на прием?'), default=False
    )
    priority = models.PositiveSmallIntegerField(
        _('Приоритет показа'), help_text='чем выше значение - тем выше в выдаче', default=0,
    )

    objects = ServiceManager()
    tree_manager = TreeManager()

    class Meta:
        verbose_name = _('Услуга')
        verbose_name_plural = _('Услуги')
        # ordering = ('-priority',)

    def __str__(self):
        level = self.get_level()
        if level == 0:
            return f"{self.title}"
        if level == 1 and self.parent:
            return f"{self.parent.title} - {self.title}"
        if level == 2 and self.parent:
            return f"--- {self.parent.title} - {self.title}"
        return f"----- {self.title}"

    def get_slug(self, postfix_number=0):
        slug = slugify(self.title, separator=self.SLUG_SEPARATOR)
        if postfix_number:
            postfix = f"{self.SLUG_SEPARATOR}{postfix_number}"
            # make slug shorter to be within field length limit with postfix
            slug = slug[: 255 - len(postfix)] + postfix
        if not Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            return slug
        return self.get_slug(postfix_number=postfix_number + 1)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_slug()
        super(Service, self).save(*args, **kwargs)

    def mark_hidden(self, save=True):
        if self.is_visible_for_appointments:
            self.is_visible_for_appointments = False
        super(Service, self).mark_hidden(save=save)


class ServicePrice(DisplayableModel):
    service = models.ForeignKey(Service, related_name="prices", on_delete=models.CASCADE)
    title = models.CharField(
        _('название'), help_text=_('первичный прием/прием по акции'), max_length=255
    )
    price = models.CharField(
        _("цена"),
        help_text=_('от 100 до 200 руб/333 руб/бесплатно'),
        max_length=250,
        db_index=True,
        null=True,
        blank=True,
    )
    code = models.CharField(_("код"), max_length=255, db_index=True, null=True, blank=True)
    priority = models.PositiveSmallIntegerField(
        _('Приоритет показа'), help_text='чем выше значение - тем выше в выдаче', default=0,
    )

    class Meta:
        verbose_name = _('Цена для услуги')
        verbose_name_plural = _('Цены для услуг')
        ordering = ('-priority',)


class DoctorToSubsidiary(models.Model):
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if DoctorToSubsidiary.objects.filter(
            doctor=self.doctor, subsidiary=self.subsidiary
        ).exists():
            doctor_id = self.doctor_id
            subsidiary_id = self.subsidiary_id
            raise IntegrityError(
                f'Doctor id {doctor_id} already exists for subsidiary id={subsidiary_id}'
            )
        super(DoctorToSubsidiary, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('связь врача с клиникой')
        verbose_name_plural = _('связи врачей с клиниками')


class DoctorToService(models.Model):
    doctor = models.ForeignKey('Doctor', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if DoctorToService.objects.filter(doctor=self.doctor, service=self.service).exists():
            raise IntegrityError(
                f'Doctor id {self.doctor_id} already exists for service id={self.service_id}'
            )
        super(DoctorToService, self).save(*args, **kwargs)

    def __str__(self):
        return f"врач: {self.doctor.short_full_name}, услуга: {self.service}"

    class Meta:
        verbose_name = _('связь врача с услугой')
        verbose_name_plural = _('связи врачей с услугами')


class Doctor(TimeStampIndexedModel, StatusModel, DeletableDisplayable):
    STATUS = DoctorStatus.CHOICES

    profile = models.OneToOneField('profiles.Profile', on_delete=models.PROTECT)
    subsidiaries = models.ManyToManyField(Subsidiary, through=DoctorToSubsidiary)
    services = models.ManyToManyField(Service, through=DoctorToService)
    description = models.TextField(_('описание'), blank=True)
    education = models.TextField(_('образование'), null=True, blank=True)
    experience = models.TextField(_('опыт (текстом)'), null=True, blank=True)
    speciality_text = models.TextField(_('специальность (текстом)'), null=True, blank=True)
    public_full_name = models.CharField(
        _('полные инициалы'),
        max_length=255,
        blank=True,
        db_index=True,
        help_text=_('показывать пользователям вместо полного имени из профиля'),
    )
    public_short_name = models.CharField(
        _('сокращенные инициалы'),
        max_length=200,
        blank=True,
        db_index=True,
        help_text=_('показывать пользователям вместо полного имени из профиля'),
    )

    integration_data = JSONField(
        verbose_name=_('Информация об интеграции с клиникой'),
        encoder=DjangoJSONEncoder,
        default=dict,
        blank=True,
    )

    is_timeslots_available_for_patient = models.BooleanField(
        _('Пациент видит талоны?'),
        default=False,
        help_text=_('Если видит - то в приложении талоны доступны для записи '),
    )
    is_fake = models.BooleanField(
        _("Сервисный?"),
        default=False,
        help_text=_("Если сервисный - то не будет показываться в списке врачей в приложении"),
    )
    is_totally_hidden = models.BooleanField(
        _("Спрятанный от всех?"),
        default=False,
        help_text=_("Если спрятанный - то его записи, услуги, упоминания будут скрыты"),
    )
    youtube_video_link = models.URLField(
        null=True, blank=True, verbose_name=_("ссылка на видеовизитку на YouTube")
    )

    objects = DoctorManager()
    all_objects = DoctorAllManager()

    @property
    def short_full_name(self) -> str:
        return self.public_short_name or self.profile.short_full_name

    @property
    def full_name(self) -> str:
        return self.public_full_name or self.profile.full_name

    @property
    def youtube_video_id(self) -> Optional[str]:
        if not self.youtube_video_link:
            return

        link = self.youtube_video_link.replace("https://www.youtube.com/watch?v=", "")
        return link

    class Meta:
        verbose_name = DOCTOR_STR
        verbose_name_plural = _('Врачи')
        default_manager_name = 'all_objects'

    def __str__(self):
        speciality = self.speciality_text
        return f"{self.short_full_name}{' '+ speciality if speciality else ''}"

    def save(self, **kwargs):
        if self.is_removed and self.status is not DoctorStatus.DELETED:
            self.status = DoctorStatus.DELETED

        if self.status in [DoctorStatus.FIRED, DoctorStatus.DELETED]:
            self.mark_hidden(save=False)

        if self.profile.full_name and not self.public_full_name:
            tmp = self.profile.full_name.split()
            if len(tmp) == 3:
                last = tmp[0].capitalize()
                first = tmp[1].capitalize()
                middle = tmp[2].capitalize()
                self.public_full_name = f"{last} {first} {middle}"

        if self.public_full_name and not self.public_short_name:
            tmp = self.public_full_name.split()
            if len(tmp) == 3:
                last = tmp[0].capitalize()
                first = tmp[1]
                middle = tmp[2]
                self.public_short_name = (
                    f"{last} {first[0].capitalize()}. {middle[0].capitalize()}."
                )
        super(Doctor, self).save(**kwargs)


class Patient(TimeStampIndexedModel, ClinicSoftDeletableModel):
    profile = models.OneToOneField('profiles.Profile', on_delete=models.PROTECT)
    integration_data = JSONField(
        verbose_name=_('Информация об интеграции с клиникой'),
        encoder=DjangoJSONEncoder,
        default=dict,
        blank=True,
        help_text='Не изменять без крайней нужды!<br/>'
        'Пример:<br/>'
        '    {"extra_subsidiary_info": [{"subsidiary_id": 1, "patient_id": 100500}]}.<br/>'
        'Важно указывать subsidiary_id филиала, где пациент есть в БД.',
    )
    # изначальная задумка: считать пациента "подтвержденным",
    # если он уже бывал в клинике хотя б 1 раз
    is_confirmed = models.BooleanField(
        _("подтвержден?"),
        default=True,
        help_text=_(
            "если пациент НЕ подтвержден - он видит только записи, которые оформил из приложения"
        ),
    )
    all_objects = models.Manager()

    @property
    def full_info(self):
        birth_date = self.profile.birth_date
        if birth_date:
            return f"{self.profile} | {birth_date.strftime(DATE_INPUT_FORMATS[0])}"
        return f"{self.profile}"

    @property
    def short_full_name(self) -> str:
        return f"{self.profile.short_full_name}"

    @property
    def full_name(self) -> str:
        return f"{self.profile.full_name}"

    def __str__(self):
        return self.short_full_name

    @property
    def user(self):
        """
        :rtype: User | None
        """
        return self.profile.user

    class Meta:
        verbose_name = _('пациент')
        verbose_name_plural = _('пациенты')


class Promotion(TimeStampIndexedModel, DisplayableModel):
    title = models.CharField(_('заголовок акции'), max_length=150, db_index=True)
    content = RichTextField(_('содержимое'), help_text=_('можно вставлять ссылки, картинки'))
    primary_image = models.ImageField(
        _('Картинка'), upload_to='promotion_images/', validators=[validate_image_max_size]
    )
    subsidiaries = models.ManyToManyField(
        Subsidiary, verbose_name=_('Филиалы, в которых акция актуальна'), blank=True
    )
    ordering_number = models.PositiveSmallIntegerField(
        _('Порядок показа'), help_text='отображение по порядку - от 1 до 100500', default=1
    )
    published_from = models.DateTimeField(_('дата старта публикации'))
    published_until = models.DateTimeField(
        _('дата окончания публикации'),
        blank=True,
        null=True,
        help_text=_('если поле не заполнено - значит, публикация бессрочная'),
    )

    class Meta:
        verbose_name = _('акция/новость')
        verbose_name_plural = _('акции/новости')
        ordering = ('-ordering_number', '-created')

    def __str__(self):
        return f'{self.title}'

    @property
    def publication_range_text(self):
        start = self.published_from and formats.date_format(self.published_from, "DATE_FORMAT")
        end = self.published_until and formats.date_format(self.published_until, "DATE_FORMAT")
        if start and end:
            return _(f'c {start} до {end}')
        elif start:
            return _(f'c {start}')

    def clean(self):
        if not self.published_until:
            return
        if self.published_from >= self.published_until:
            raise ValidationError(_('Время начало публикации должно быть раньше времени окончания'))

    def save(self, **kwargs):
        self.full_clean()
        super(Promotion, self).save(**kwargs)

    objects = PromotionQuerySet.as_manager()
