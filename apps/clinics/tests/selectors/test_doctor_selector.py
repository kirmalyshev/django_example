from copy import deepcopy

from django.test import TestCase

from apps.clinics.factories import DoctorFactory, ServiceFactory, SubsidiaryFactory
from apps.clinics.selectors import DoctorSelector


class DoctorSelectorBasicTest(TestCase):
    doctor_descriptions = ("first", "second", "third")
    selector = DoctorSelector()

    def setUp(self):
        self.doctor_list = [DoctorFactory(description=x) for x in self.doctor_descriptions]
        self.doctor_set = set(self.doctor_list)

    def test_all__multiple(self):
        self.assertEqual(set(self.selector.all()), self.doctor_set)

    def test_all__mixed_with_removed(self):
        doctor_removed = DoctorFactory(is_removed=True)
        self.assertEqual(set(self.selector.all()), self.doctor_set)

    def test_all__delete_single(self):
        self.doctor_list[0].is_removed = True
        self.doctor_list[0].save()
        self.assertEqual(set(self.selector.all()), set(self.doctor_list[1:]))

    def test_all_with_deleted__multiple(self):
        self.assertEqual(set(self.selector.all_with_deleted()), self.doctor_set)

    def test_all_with_deleted__add_deleted(self):
        new_removed = DoctorFactory(is_removed=True)
        # self.doctor_list.append(new_removed)
        new_set = deepcopy(self.doctor_set)
        new_set.add(new_removed)
        self.assertEqual(set(self.selector.all_with_deleted()), new_set)

    def test_all_with_deleted__add_not_deleted(self):
        self.doctor_list.append(DoctorFactory(is_removed=False))
        self.assertQuerysetEqual(
            list(self.selector.all_with_deleted()),
            self.doctor_list,
            transform=lambda x: x,
            ordered=False,
        )

    def test_all_with_deleted__delete_single(self):
        self.doctor_list[0].is_removed = True
        self.doctor_list[0].save()
        self.assertEqual(
            set(self.selector.all_with_deleted()), self.doctor_set, self.doctor_set,
        )

    def test_visible_to_patient(self):
        removed = DoctorFactory(is_removed=True, is_displayed=True)
        hidden = DoctorFactory(is_removed=False, is_displayed=False)
        removed_and_hidden = DoctorFactory(is_removed=True, is_displayed=False)

        qs = self.selector.visible_to_patient()
        self.assertNotIn(removed, qs)
        self.assertNotIn(hidden, qs)
        self.assertNotIn(removed_and_hidden, qs)
        self.assertEqual(
            set(qs), self.doctor_set,
        )


class DoctorSelectorFilterTest(TestCase):
    selector = DoctorSelector()

    @classmethod
    def setUpTestData(cls):
        cls.subsidiary_first = SubsidiaryFactory(title="first")
        cls.subsidiary_second = SubsidiaryFactory(title="second")
        cls.service_first = ServiceFactory(title="first")
        cls.service_second = ServiceFactory(title="second")

        cls.doctor_first = DoctorFactory(
            subsidiaries=[cls.subsidiary_first], services=[cls.service_first], description="first"
        )
        cls.doctor_second = DoctorFactory(
            subsidiaries=[cls.subsidiary_second],
            services=[cls.service_second],
            description="second",
        )
        cls.doctor_mixed = DoctorFactory(
            subsidiaries=[cls.subsidiary_first, cls.subsidiary_second],
            services=[cls.service_first, cls.service_second],
            description="mixed",
        )
        cls.doctor_none = DoctorFactory(description="none")
        cls.all_doctors = cls.selector.all()

    def test_filter_by_params__subsidiary_first(self):
        self.assertEqual(
            set(
                self.selector.filter_by_params(
                    self.all_doctors, subsidiary_ids=[self.subsidiary_first.id]
                )
            ),
            {self.doctor_first, self.doctor_mixed},
        )

    def test_filter_by_params__service_first(self):
        self.assertEqual(
            set(
                self.selector.filter_by_params(
                    self.all_doctors, service_ids=[self.service_first.id]
                )
            ),
            {self.doctor_first, self.doctor_mixed},
        )

    def test_filter_by_params__subsidiary_second(self):
        self.assertEqual(
            set(
                self.selector.filter_by_params(
                    self.all_doctors, subsidiary_ids=[self.subsidiary_second.id]
                )
            ),
            {self.doctor_second, self.doctor_mixed},
        )

    def test_filter_by_params__service_second(self):
        self.assertEqual(
            set(
                self.selector.filter_by_params(
                    self.all_doctors, service_ids=[self.service_second.id]
                )
            ),
            {self.doctor_second, self.doctor_mixed},
        )

    def test_filter_by_params__no_filter(self):
        self.assertQuerysetEqual(
            list(self.selector.filter_by_params(self.all_doctors)),
            [self.doctor_first, self.doctor_second, self.doctor_mixed, self.doctor_none],
            transform=lambda x: x,
            ordered=False,
        )

    def test_filter_by_params__both_subsidiaries(self):
        self.assertEqual(
            set(
                self.selector.filter_by_params(
                    self.all_doctors,
                    subsidiary_ids=[self.subsidiary_first.id, self.subsidiary_second.id],
                )
            ),
            {self.doctor_first, self.doctor_second, self.doctor_mixed},
        )

    def test_filter_by_params__both_services(self):
        self.assertEqual(
            set(
                self.selector.filter_by_params(
                    self.all_doctors, service_ids=[self.service_first.id, self.service_second.id]
                )
            ),
            {self.doctor_first, self.doctor_second, self.doctor_mixed},
        )

    def test_filter_by_params__nonexistent_service_id(self):
        self.assertEqual(
            list(self.selector.filter_by_params(self.all_doctors, service_ids=[123456])), []
        )

    def test_filter_by_params__nonexistent_subsidiary_id(self):
        self.assertEqual(
            list(self.selector.filter_by_params(self.all_doctors, subsidiary_ids=[123456])), []
        )

    def test_filter_by_params__bad_service_id_type(self):
        with self.assertRaises(ValueError):
            self.selector.filter_by_params(self.all_doctors, service_ids=["hello world!"])

    def test_filter_by_params__bad_subsidiary_id_type(self):
        with self.assertRaises(ValueError):
            self.selector.filter_by_params(self.all_doctors, subsidiary_ids=["hello world!"])

    def test_filter_by_params__bad_keyword_arg(self):
        self.assertQuerysetEqual(
            list(
                self.selector.filter_by_params(
                    self.all_doctors,
                    services_ids=[self.service_first.id],
                    subsidiaries_ids=[self.subsidiary_first.id],
                )
            ),
            [self.doctor_first, self.doctor_second, self.doctor_mixed, self.doctor_none],
            transform=lambda x: x,
            ordered=False,
        )
