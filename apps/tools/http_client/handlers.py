import re

from user_agents import parse as parse_user_agent

from .constants import APPLE_DEVICE_NAMES, MobilePlatforms, MobileApps


class HttpClientHandler(object):
    """
    Handler for getting additional information about remote http client

    Note: old iOS application versions for customers send the same user agent value as universal one.
    It's parsed in the same way. New versions of iOS applications for customers have unique user agent

    There are two generations of mobile applications user agents.
    The first generation is deprecated now. Actual user agent template confirms to
    RFC standard (https://tools.ietf.org/html/rfc7231#section-5.5.3).

    Actual mobile agents templates:
        <app type>/<app version> (<device name>) <os>/<os version>

    Important note: iOS mobile applications send device code instead of verbose device name.
    It should be converted into familiar name with special dictionaries

    Information that can be retrieved:
        - mobile app platform, version and kind of application
        - information about browser and os
        - is remote client a mobile app or browser
    """

    mobile_app_version_regex = re.compile('django_example(?:FC){0,1}/(?P<app_version>[\d.]+)')
    is_mobile_app = False
    os_name = None
    os_version = None
    name = None
    version = None
    app_kind = None
    device_name = None

    def __init__(self, user_agent):
        self.user_agent = user_agent

        if not self.user_agent:
            return

        self.is_mobile_app = MobileApps.mobile_app_name in user_agent
        if self.is_mobile_app:
            self._parse_rfc_mobile_user_agent()
        else:
            self._parse_browser_user_agent()

    def _parse_rfc_mobile_user_agent(self):
        # new mobile user agents have RFC format, so data can be retrieved by common parser
        parser = parse_user_agent(self.user_agent)
        self.os_name = parser.os.family
        self.os_version = parser.os.version_string
        if self.os_name == MobilePlatforms.ios:
            # IOS devices provide special code in agent instead of verbose device name
            device_code = parser.device.model
            self.device_name = APPLE_DEVICE_NAMES.get(device_code, None)
        elif self.os_name == MobilePlatforms.android:
            self.device_name = parser.device.family

        # we use custom token to identify application name and its version, that data can't be retrieved by parser
        self.app_kind = MobileApps.for_patients
        self.name = MobileApps.application_kinds[self.app_kind]
        match = self.mobile_app_version_regex.search(self.user_agent)
        if match:
            self.version = match.groups()[0]

    def _parse_browser_user_agent(self):
        parser = parse_user_agent(self.user_agent)
        self.os_name = parser.os.family
        self.os_version = parser.os.version_string
        self.name = parser.browser.family
        self.version = parser.browser.version_string
        self.device_name = parser.device.family
