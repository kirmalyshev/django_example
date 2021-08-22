from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.clinics.factories import SubsidiaryFactory
from apps.clinics.models import SubsidiaryImage
from apps.tools.apply_tests.utils import touch_media_files


class SubsidiaryImageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subsidiary = SubsidiaryFactory()
        image_names = ['hello.jpg', 'world.jpg']
        touch_media_files(image_names)

    def test_save__unset_primary(self):
        image_1 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='hello.jpg'
        )
        self.assertTrue(image_1.is_primary)

        image_2 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='world.jpg'
        )
        self.assertTrue(image_2.is_primary)

        image_1.is_primary = True
        image_1.save()

        image_1.refresh_from_db()
        image_2.refresh_from_db()

        self.assertTrue(image_1.is_primary)
        self.assertFalse(image_2.is_primary)

    def test_clean__ok(self):
        image_1 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='hello.jpg'
        )
        image_1.clean()
        self.assertTrue(image_1.is_primary)

    def test_clean__raises(self):
        image_1 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='hello.jpg'
        )
        image_2 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=False, picture='world.jpg'
        )
        with self.assertRaises(ValidationError):
            image_2.is_primary = True
            image_2.clean()
