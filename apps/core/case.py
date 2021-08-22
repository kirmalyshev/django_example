from apps.profiles.factories import UserFactory
from apps.tools.apply_tests.case import BaseDRFTest


class SimpleDRFTest(BaseDRFTest):
    password = None

    def login(self):
        """
        Login user method
        """
        username, password = self.username, self.password
        if not all([username, password]):
            password = 123
            user = UserFactory(password=password)
            username = user.username

        self.client.login(username=username, password=password)
