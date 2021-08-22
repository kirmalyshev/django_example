from django.test import TestCase

from apps.clinics.factories import PatientFactory
from apps.clinics.selectors import PatientSelector


class PatientSelectorTest(TestCase):
    maxDiff = None
    selector = PatientSelector()

    def setUp(self):
        self.patient_list = [PatientFactory() for x in range(3)]

    def test_all__multiple(self):
        self.assertEqual(list(self.selector.all()), self.patient_list)

    def test_all__mixed_with_deleted(self):
        patient_removed = PatientFactory(is_removed=True)
        self.assertEqual(list(self.selector.all()), self.patient_list)

    def test_all__delete_single(self):
        self.patient_list[0].is_removed = True
        self.patient_list[0].save()
        self.assertEqual(list(self.selector.all()), self.patient_list[1:])

    def test_all__add_single(self):
        self.patient_list.append(PatientFactory())
        self.assertEqual(list(self.selector.all()), self.patient_list)

    def test_all_with_deleted__multiple(self):
        self.assertEqual(list(self.selector.all_with_deleted()), self.patient_list)

    def test_all_with_deleted__add_removed(self):
        self.patient_list.append(PatientFactory(is_removed=True))
        self.assertEqual(list(self.selector.all_with_deleted()), self.patient_list)

    def test_all_with_deleted__remove(self):
        self.patient_list[0].is_removed = True
        self.patient_list[0].save()
        self.assertQuerysetEqual(
            list(self.selector.all_with_deleted()),
            self.patient_list,
            transform=lambda x: x,
            ordered=False,
        )

    def test_all_for_integration__multiple(self):
        for model in self.selector.all_for_integration():
            self.assertTrue(hasattr(model, "_prefetched_objects_cache"))
