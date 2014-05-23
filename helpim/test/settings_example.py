# Do not thouch this line, needed for the settings
from selenium import webdriver

# Site where the installation of HelpIM to test is running
# the script expects a default setup
testSite = "https://testchat.mysite.example/"

# Staff accounts for testing, should have normal priority
testAccounts = [
    {'username': 'user1',
     'password': 'password'},
    {'username': 'user2',
     'password': 'password'},
    {'username': 'user3',
     'password': 'password'},
    {'username': 'user4',
     'password': 'password'},
    {'username': 'user5',
     'password': 'password'},
    {'username': 'user6',
     'password': 'password'}]

# Staff accounts for testing, should have high priority
testAccountsHighPriority = [
    {'username': 'userhighprio',
     'password': 'password'}]

# How long to wait for UI element that are expected to appear.
# Value should depend on speed of test system, test site and
# connection between them.
timeout = 15

# Local browsers available for testing, the first one is used for tests
# that are not about browser compatibility, all others are used for
# browser compatibility tests
# Possible values are: Firefox, Chrome, IE, Opera, Safari
#localBrowsers = ["Firefox", "Chrome"]
localBrowsers = ["Firefox"]

# Set to 'True' if you want firefox to load plugins. All xpi files
# from the directory this script is executed from are loaded. This
# is usefull for debugging the tests with Firebug. Set to 'False' when
# not needed.
firefoxPlugins = True

# URL for the default remote testing service to use. Can be overridden
# in the remoteBrowsers definition
remoteExecutor = "http://user:password@hub.testingprovider.example/"

# List of remote browsers to use for tesing. If a different remote execution
# is needed, add it like this:
# 'version': "11"}, "http://excuter.example/path"),
remoteBrowsers = {
# Firefox seems to be hit by this bug:
# http://code.google.com/p/selenium/issues/detail?id=6112
#    "Linux_FF29": (webdriver.DesiredCapabilities.FIREFOX,
#                   {'platform': "Linux",
#                    'version': "29"}),
#    "Linux_FF24": (webdriver.DesiredCapabilities.FIREFOX,
#                   {'platform': "Linux",
#                    'version': "24"}),
# IE11 on Windows 8.1 this one seems to have a issue with selenium,
# it is not reacting to stored cookies
#    "W81_IE11": (webdriver.DesiredCapabilities.INTERNETEXPLORER,
#               {'platform': "Windows 8.1",
#                'version': "11"}),
#    "W80_IE10": (webdriver.DesiredCapabilities.INTERNETEXPLORER,
#               {'platform': "Windows 8",
#                'version': "10"}),
#    "W7_IE11": (webdriver.DesiredCapabilities.INTERNETEXPLORER,
#               {'platform': "Windows 7",
#                'version': "11"}),
#    "W7_IE10": (webdriver.DesiredCapabilities.INTERNETEXPLORER,
#               {'platform': "Windows 7",
#                'version': "10"}),
#    "W7_IE9": (webdriver.DesiredCapabilities.INTERNETEXPLORER,
#               {'platform': "Windows 7",
#                'version': "9"}),
#    "W7_IE8": (webdriver.DesiredCapabilities.INTERNETEXPLORER,
#               {'platform': "Windows 7",
#                'version': "8"}),
    }

# Path to store screenshots, can be relative or absolute
screenshotPath = "./screenshots"

