from apps.clinics.factories import SubsidiaryFactory

subsidiary_titles = ['На Ленина 01', 'На Советском 02', 'На Кирова 03', 'На Князева 04']


def load():
    for title in subsidiary_titles:
        SubsidiaryFactory(title=title)
