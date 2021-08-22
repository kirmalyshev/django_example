from django.test import TestCase

from apps.clinics.factories import ServiceFactory, SubsidiaryFactory
from apps.clinics.selectors import ServiceSelector


class ServiceSelectorTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subsidiary_map = {
            0: SubsidiaryFactory(),
            1: SubsidiaryFactory(),
            2: SubsidiaryFactory(),
        }
        cls.selector = ServiceSelector()
        cls.qs = cls.selector.all()
        cls.service_titles = ("first", "second", "third")

    def setUp(self):
        self.service_list = [
            ServiceFactory(title=x, subsidiaries=[self.subsidiary_map[idx].id])
            for idx, x in enumerate(self.service_titles)
        ]
        self.service_list_ids = [service.id for service in self.service_list]

    def test_all__multiple(self):
        self.assertEqual(set(self.selector.all()), set(self.service_list))

    def test_all__add_one(self):
        self.service_list.append(ServiceFactory(title="fourth"))
        self.assertEqual(set(self.selector.all()), set(self.service_list))

    def test_all__check_title(self):
        [self.assertIn(x.title, self.service_titles) for x in self.selector.all()]

    def test_filter_by_params__no_filter(self):
        self.assertEqual(
            list(self.selector.filter_by_params(self.qs).values_list('id', flat=True)),
            self.service_list_ids,
        )

    def test_filter_by_params__filter_first(self):
        self.assertEqual(
            list(
                self.selector.filter_by_params(self.qs, subsidiary_ids=[self.subsidiary_map[0].id])
            ),
            [self.service_list[0]],
        )

    def test_filter_by_params__filter_first_and_second(self):
        self.assertEqual(
            list(
                self.selector.filter_by_params(
                    self.qs, subsidiary_ids=[self.subsidiary_map[0].id, self.subsidiary_map[1].id]
                )
            ),
            self.service_list[:-1],
        )

    def test_filter_by_params__filter_mixed_element(self):
        self.service_list.pop(-1)
        self.service_list.append(
            ServiceFactory(subsidiaries=[self.subsidiary_map[0].id, self.subsidiary_map[1].id])
        )
        self.assertEqual(
            list(
                self.selector.filter_by_params(
                    self.qs, subsidiary_ids=[self.subsidiary_map[0].id, self.subsidiary_map[1].id]
                )
            ),
            list(self.service_list),
        )

    def test_filter_by_params__nonexistent_subsidiary_id(self):
        self.assertEqual(list(self.selector.filter_by_params(self.qs, subsidiary_ids=[123456])), [])

    def test_filter_by_params__bad_subsidiary_id_type(self):
        with self.assertRaises(ValueError):
            self.selector.filter_by_params(self.qs, subsidiary_ids=["hello world"])

    def test_filter_by_params__bad_keyword_arg(self):
        self.assertEqual(
            set(self.selector.filter_by_params(self.qs, subsidiaries_ids=[123456])),
            set(self.service_list,),
        )

    def test_visible_to_patient(self):
        hidden = ServiceFactory(is_displayed=False)

        qs = self.selector.visible_to_patient()
        self.assertNotIn(hidden, qs)
        self.assertEqual(
            set(qs), set(self.service_list),
        )
