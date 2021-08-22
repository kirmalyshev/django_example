from django.test import TestCase

from apps.clinics.factories import SubsidiaryFactory
from apps.clinics.selectors import SubsidiarySelector


class SubsidiarySelectorTest(TestCase):
    subsidiary_titles = ("first", "second", "third")
    selector = SubsidiarySelector()

    def setUp(self):
        self.subsidiary_list = [SubsidiaryFactory(title=x) for x in self.subsidiary_titles]

    def test_all__multiple(self):
        self.assertEqual(set(self.selector.all()), set(self.subsidiary_list))

    def test_all__add_single(self):
        self.subsidiary_list.append(SubsidiaryFactory())
        self.assertEqual(set(self.selector.all()), set(self.subsidiary_list))

    def test_all__mixed_with_deleted(self):
        subsidiary_removed = SubsidiaryFactory(is_removed=True)
        self.assertEqual(list(self.selector.all()), self.subsidiary_list)

    def test_all__delete_single(self):
        self.subsidiary_list[0].is_removed = True
        self.subsidiary_list[0].save()
        self.assertEqual(list(self.selector.all()), self.subsidiary_list[1:])

    def test_all__check_title(self):
        [self.assertIn(x.title, self.subsidiary_titles) for x in self.selector.all()]

    def test_all_with_deleted__multiple(self):
        self.assertEqual(list(self.selector.all_with_deleted()), self.subsidiary_list)

    def test_all_with_deleted__check_title(self):
        [self.assertIn(x.title, self.subsidiary_titles) for x in self.selector.all_with_deleted()]

    def test_all_with_deleted__add_removed(self):
        self.subsidiary_list.append(SubsidiaryFactory(is_removed=True))
        self.assertEqual(list(self.selector.all_with_deleted()), self.subsidiary_list)

    def test_all_with_deleted__remove(self):
        self.subsidiary_list[0].is_removed = True
        self.subsidiary_list[0].save()
        self.assertQuerysetEqual(
            list(self.selector.all_with_deleted()),
            self.subsidiary_list,
            transform=lambda x: x,
            ordered=False,
        )

    def test_visible_to_patient(self):
        removed = SubsidiaryFactory(is_removed=True, is_displayed=True)
        hidden = SubsidiaryFactory(is_removed=False, is_displayed=False)
        removed_and_hidden = SubsidiaryFactory(is_removed=True, is_displayed=False)

        qs = self.selector.visible_to_patient()
        self.assertNotIn(removed, qs)
        self.assertNotIn(hidden, qs)
        self.assertNotIn(removed_and_hidden, qs)
        self.assertEqual(
            set(qs), set(self.subsidiary_list),
        )
