from django.test import TestCase

from apps.clinics.factories import SubsidiaryFactory
from apps.clinics.models import SubsidiaryImage, Subsidiary
from apps.tools.apply_tests.utils import touch_media_files


class SubsidiaryTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subsidiary = SubsidiaryFactory()
        image_names = ['hello.jpg', 'world.jpg']
        touch_media_files(image_names)

    def test_primary_image_ok(self):
        image = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='hello.jpg'
        )
        self.assertEqual(image.picture, self.subsidiary.primary_image)

    def test_primary_image_multiple(self):
        image_1 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='hello.jpg'
        )
        image_2 = SubsidiaryImage.objects.create(
            subsidiary=self.subsidiary, is_primary=True, picture='world.jpg'
        )

        self.assertEqual(image_2.picture, self.subsidiary.primary_image)

    def test_mark_hidden(self):
        doctor: Subsidiary = SubsidiaryFactory(is_displayed=True)
        self.assertTrue(doctor.is_displayed)
        doctor.mark_hidden()
        updated_doctor = Subsidiary.objects.get(id=doctor.id)
        self.assertFalse(updated_doctor.is_displayed)

    def test_mark_displayed(self):
        doctor: Subsidiary = SubsidiaryFactory(is_displayed=False)
        self.assertFalse(doctor.is_displayed)
        doctor.mark_displayed()
        updated_doctor = Subsidiary.objects.get(id=doctor.id)
        self.assertTrue(updated_doctor.is_displayed)

    def test_delete__marked_hidden(self):
        doctor: Subsidiary = SubsidiaryFactory(is_displayed=True, is_removed=False)
        self.assertTrue(doctor.is_displayed)
        doctor.delete()
        updated_doctor = Subsidiary.all_objects.get(id=doctor.id)
        self.assertFalse(updated_doctor.is_displayed)
        self.assertTrue(updated_doctor.is_removed)
