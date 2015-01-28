#!/usr/bin/python
# -*- coding: utf-8 -*-
# needs python selenium bindings, unfortunately available in Debian
# use: sudo easy_install install selenium or sudo pip install selenium
#
# tests can be run individually by using:
# > python browser_test.py
# and then run tests one by one:
# >>> test_closed()
# or by running the tests with py.test (pytest package)

import os
import time
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# get settings.py, should be in same directory as this script.
# Adapt settings_example.py and rename to settings.py to get started
from settings import *

# some global counters and constants
browserInstanceCount = 0
screenshotCount = 0
screenshotSubDir = time.strftime("%Y-%m-%d_%H%M%S")

def getBrowserPairs():
    browserList = localBrowsers + remoteBrowsers.keys()
    return zip(browserList, browserList[-1:] + browserList[:-1])

class RemoteSettings:
    """Handle settings for remote browser sites"""
    def __init__(self, browserId, name=""):
        self.getCaps(browserId, name)
        self.getExecutor(browserId)

    def getCaps(self, browserId, name):
        # trap with indexError when browser is not known
        self.caps = remoteBrowsers[browserId][0].copy()
        for capsAttName in remoteBrowsers[browserId][1].keys():
            self.caps[capsAttName] = remoteBrowsers[browserId][1][capsAttName]
        self.caps["name"] = "%s (%s)" % (name, browserId)

    def getExecutor(self, browserId):
        if len(remoteBrowsers[browserId])>2:
            self.executor = remoteBrowsers[browserId][2]
        else:
            self.executor = remoteExecutor

class Browser:
    """Baseclass for a browser to use for testing HelpIM"""
    def __init__(self, browserId=None, name="", firefoxPlugins=False):
        if not browserId:
            allBrowsers = localBrowsers + remoteBrowsers.keys()
            if not allBrowsers:
                raise Exception("No browsers defined in settings")
            browserId = allBrowsers[0]
        if browserId == "Chrome":
            # note the chromedriver is not in a correct path in Debian,
            # make a symlink to /usr/lib/chromium/chromedriver
            self.driver = webdriver.Chrome()
        elif browserId == "Firefox":
            if firefoxPlugins:
                profile = webdriver.FirefoxProfile()
                for fle in os.listdir("."):
                    if fle.endswith(".xpi"):
                        profile.add_extension(extension=fle)
                        #Avoid startup screen
                        flesplit = fle.split("-")
                        if flesplit[0] == "firebug":
                            profile.set_preference("extensions.firebug.currentVersion", flesplit[1])
                self.driver = webdriver.Firefox(firefox_profile=profile)
            else:
                self.driver = webdriver.Firefox()
        elif browserId == "IE":
            self.driver = webdriver.IE()
        elif browserId == "Opera":
            self.driver = webdriver.Opera()
        elif browserId == "Safari":
            self.driver = webdriver.Safari()
        else:
            remotesettings = RemoteSettings(browserId, name)
            self.driver = webdriver.Remote(
                desired_capabilities = remotesettings.caps,
                command_executor = remotesettings.executor)
        self.browserId = browserId
        global browserInstanceCount
        browserInstanceCount += 1
        self.instance = browserInstanceCount + 0
        self.lineCount = 0
        self.screenshotPath = os.path.abspath(
            os.path.join(screenshotPath, screenshotSubDir))
        try:
            os.makedirs(self.screenshotPath)
        except OSError:
            if not os.path.isdir(self.screenshotPath):
                raise
        return

    def waitForXPath(self, XPath, text=None, timeout=timeout, timingClass=None):
        self.waitFor(By.XPATH, XPath, text, timeout, timingClass)

    def waitForID(self, ID, text=None, timeout=timeout, timingClass=None):
        self.waitFor(By.ID, ID, text, timeout, timingClass)

    def waitForTag(self, Tag, text=None, timeout=timeout, timingClass=None):
        self.waitFor(By.TAG_NAME, Tag, text, timeout, timingClass)

    def waitForClass(self, Class, text=None, timeout=timeout, timingClass=None):
        self.waitFor(By.CLASS_NAME, Class, text, timeout, timingClass)

    def waitForName(self, Name, text=None, timeout=timeout, timingClass=None):
        self.waitFor(By.NAME, Name, text)

    def waitForSelector(self, Selector, text=None, timeout=timeout, timingClass=None):
        self.waitFor(By.CSS_SELECTOR, Selector, text, timeout, timingClass)

    def waitFor(self, by, search, text=None, timeout=timeout, timingClass=None):
        # fail with exception, should be caught by testframework
        if text:
            WebDriverWait(self.driver, timeout).until(
                EC.text_to_be_present_in_element((by, search), text))
        else:                
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, search)))

    def waitForTitle(self, title, timeout=timeout, timingClass=None):
        WebDriverWait(self.driver, timeout).until(
            EC.title_is(title))

    def waitForChatLine(self, line, timeout=timeout, timingClass="chatline"):
        self.waitForXPath("(//div[@class='roomMessage groupchat_message' and not(ancestor::div[contains(@style,'display: none')])])[last()]",
                          line, timeout, timingClass)

    def sendChatLine(self, line = None, send=True):
        xpath = "//div[@id='tab_content']//textarea[not(ancestor::div[contains(@style,'display: none')])]"
        WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable,
                                                  (By.XPATH, xpath))
        sendTextarea = self.driver.find_element_by_xpath(xpath)
        sendTextarea.click()
        if not line:
            self.lineCount += 1
            line = "I am %s, using a %s browser (instance %d) and sending line: %d" %(
                self.role,
                self.browserId,
                self.instance,
                self.lineCount)
        sendTextarea.send_keys(line)
        if send:
            sendTextarea.send_keys(Keys.ENTER)
        return line

    def getLastChatLine(self, delay=1):
        time.sleep(delay)
        return self.driver.find_element_by_xpath("(//div[@class='roomMessage groupchat_message' and not(ancestor::div[contains(@style,'display: none')])])[last()]").text.split("> ")[1]

    def peerIsTyping(self):
        line = self.getTypingNotificationLine()
        if line:
            return line[-16:] == u"is aan het typen"
        else:
            return False

    def peerStoppedTyping(self):
        line = self.getTypingNotificationLine()
        if line:
            return line[-20:] == u"is gestopt met typen"
        else:
            return False

    def getTypingNotificationLine(self):
        divs = self.driver.find_elements_by_xpath("//div[@class='roomMessage composingMessage']")
        if divs:
            return divs[0].text
        else:
            return False

    def closeActiveChat(self, confirm=False):
        self.driver.find_element_by_xpath("//div[@id='logoutButton']/div").click()
        if confirm:
            self.waitForXPath('(//button[@name="ok"])[last()]')
            self.getScreenshot("close_confirmation")
            self.driver.find_element_by_xpath('(//button[@name="ok"])[last()]').click()

    def submitQuestionnaire(self, wait=False):
        """Enter values in radio-buttons (first one will be selected) and type
           'testing with selenium' in textfields and textareas. Send in with
           Submit."""
        self.waitForXPath("//*[@class='modal-dialog modal-dialog-questionnaire' and not(contains(@style, 'display: none'))]/div[1]")
        # pick the last iframe
        iframes = self.driver.find_elements_by_xpath("//iframe")
        self.driver.switch_to_frame(len(iframes)-1)
        self.waitForXPath("html/body/form")
        form = self.driver.find_element_by_xpath("html/body/form")
        inputs = form.find_elements_by_tag_name("input")
        for inpt in inputs:
            if inpt.get_attribute("type") == "radio":
                # click on the first one
                if inpt.get_attribute("id").split("_")[3] == "0":
                    inpt.click()
            if inpt.get_attribute("type") == "text":
                inpt.send_keys("Testing with Selenium")
            if inpt.get_attribute("type") == "submit":
                submit = inpt
        textareas = form.find_elements_by_tag_name("textarea")
        for textarea in textareas:
            textarea.send_keys("Testing with Selenium")
        self.getScreenshot("form")
        submit.click()
        self.driver.switch_to_default_content()
        if wait:
            # This works great on firefox, but f***ing chrome thinks
            # everything under the iframe is clickable. So just stupidly
            # wait for a stupid browser...
            #WebDriverWait(self.driver, timeout).until(
            #    EC.element_to_be_clickable((By.XPATH, "//body/div[1]")))
            self.getScreenshot("form_submitted")
            time.sleep(5)

    def close(self):
        self.driver.quit()

    def getScreenshot(self, ID):
        global screenshotCount
        screenshotCount += 1
        filename = "".join((str(screenshotCount), "_",
                            self.browserId, "_",
                            str(self.instance), "_",
                            self.role, "_",
                            ID, ".png"))
        fullpath = os.path.join(self.screenshotPath, filename)
        self.driver.get_screenshot_as_file(fullpath)

class StaffBrowser(Browser):
    """Browser to use for testing HelpIM as staff"""
    def __init__(self, browserId=None, name="", firefoxPlugins=False):
        self.role = "Staff"
        Browser.__init__(self, browserId, name, firefoxPlugins)

    def login(self, user=0, highPriority=False):
        if highPriority:
            credentials = testAccountsHighPriority[user]
        else:
            credentials = testAccounts[user]
        self.driver.get(testSite + "login")
        self.waitForXPath(".//*[@id='login-form']/div[4]/input")
        self.driver.find_element_by_id("id_username").clear()
        self.driver.find_element_by_id("id_username").send_keys(credentials['username'])
        self.driver.find_element_by_id("id_password").clear()
        self.driver.find_element_by_id("id_password").send_keys(credentials['password'])
        self.driver.find_element_by_tag_name("form").submit()
        self.waitForXPath(".//*[@id='content']/h1")

    def openGroupchat(self):
        self.driver.find_element_by_xpath(".//*[@id='navigation']/ul/li[2]/a").click()
        self.waitForClass("sendTextarea")

    def openCarechat(self):
        self.driver.find_element_by_xpath("//div[@class='requestClientButton']/div").click()
        self.waitForXPath("html/body/div[1]/div[2]/div/div[2]/table/tbody/tr[2]/td/div")

    def waitForClient(self, timeout=timeout):
        self.waitForXPath("(//div[@class='messagesPanel' and not(ancestor::div[contains(@style,'display: none')])])[1]/div[2]", text="Je hebt een gesprek met", timeout=timeout)

    def getClientFormId(self):
        src = self.driver.find_element_by_xpath("//div[@class='messagesPanel']//iframe").get_attribute('src')
        return int(src.split("/")[-2])

    def getOwnNick(self):
        welcomeMessage = self.driver.find_element_by_xpath("(//div[@class='messagesPanel' and not(ancestor::div[contains(@style,'display: none')])])[1]/div[1]").text
        return welcomeMessage[7:-38] #assumes Dutch translation

    def getPeerNick(self):
        joinMessage = self.driver.find_element_by_xpath("(//div[@class='messagesPanel' and not(ancestor::div[contains(@style,'display: none')])])[1]/div[2]").text
        return joinMessage[24:] #assumes Dutch translation


class ClientBrowser(Browser):
    """Browser to test HelpIM as client"""
    def __init__(self, browserId=None, name="", firefoxPlugins=False):
        self.role = "Client"
        Browser.__init__(self, browserId, name, firefoxPlugins)

    def start(self):
        self.driver.get(testSite)

    def enterNick(self, nickname):
        self.waitForID("muc_nick")
        self.driver.find_element_by_id("muc_nick").send_keys(nickname)
        self.driver.find_element_by_xpath("html/body/div[4]/div[3]/button[1]").click()

    def getQueuePos(self):
        try:
            self.waitForID("waitingroom_message")
        except selenium.common.exceptions.TimeoutException:
            return False
        queueline = self.driver.find_element_by_id("waitingroom_message").text
        return int(queueline.split()[4])

    def waitForChat(self, timeout=timeout):
        self.waitForXPath("(//div[@class='messagesPanel' and not(ancestor::div[contains(@style,'display: none')])])[1]/div[1]", text="Je hebt een gesprek met")

    def confirmExit(self):
        self.waitForXPath("//button[@name='ok' and not(ancestor::div[contains(@style,'display: none')])]")
        self.driver.find_element_by_xpath("//button[@name='ok' and not(ancestor::div[contains(@style,'display: none')])]").click()

class StatusBrowser(Browser):
    """Browser to test status xml"""
    def __init__(self, browserId=None, name="", firefoxPlugins=False):
        self.role = "XML status checker"
        Browser.__init__(self, browserId, name, firefoxPlugins)

    def getStatus(self):
        self.driver.get(testSite + "status.xml")
        self.waitForXPath("/status")
        copen = self.driver.find_element_by_xpath("/status/open").text == "True"
        chatting = int(self.driver.find_element_by_xpath("/status/chatting").text)
        return (copen, chatting)

def typing_notification_check(Send, Receive, screenshot = False):
    """utility function to check the typing notification"""
    acceptable_delay = 2
    assert Send.peerIsTyping() == False
    assert Send.peerStoppedTyping() == False
    assert Receive.peerIsTyping() == False
    assert Receive.peerStoppedTyping() == False
    Send.sendChatLine('X', send=False)
    time.sleep(acceptable_delay)
    if screenshot:
        Receive.getScreenshot("typing")
    assert Send.peerIsTyping() == False
    assert Send.peerStoppedTyping() == False
    assert Receive.peerIsTyping()
    assert Receive.peerStoppedTyping() == False
    time.sleep(10+acceptable_delay)
    if screenshot:
        Receive.getScreenshot("stopped_typing")
    assert Send.peerIsTyping() == False
    assert Send.peerStoppedTyping() == False
    assert Receive.peerIsTyping() == False
    assert Receive.peerStoppedTyping()
    Send.sendChatLine(Keys.BACK_SPACE, send=False)
    Receive.waitForChatLine(Send.sendChatLine())
    assert Send.peerIsTyping() == False
    assert Send.peerStoppedTyping() == False
    assert Receive.peerIsTyping() == False
    assert Receive.peerStoppedTyping() == False

def test_compatibility():
    """Iterates over the browsers defined in settings and lets each of
       them chat as client and as staff. Making nice screenshots on the
       way."""
    for cBrowser, sBrowser in getBrowserPairs():
        c1 = ClientBrowser(cBrowser, firefoxPlugins=firefoxPlugins)
        s1 = StaffBrowser(sBrowser, firefoxPlugins=firefoxPlugins)
        s1.login(0)
        s1.openGroupchat()
        s1.getScreenshot("groupchat")
        c1.start()
        c1.enterNick("testbrowser")
        c1.submitQuestionnaire(wait=True)
        assert c1.getQueuePos() == 1
        c1.getScreenshot("queue")
        s1.openCarechat()
        s1.waitForClient()
        c1.waitForChat()
        typing_notification_check(c1, s1, screenshot=True)
        typing_notification_check(s1, c1, screenshot=True)
        for x in range(10):
            c1.waitForChatLine(s1.sendChatLine())
            s1.waitForChatLine(c1.sendChatLine())
        typing_notification_check(c1, s1, screenshot=True)
        typing_notification_check(s1, c1, screenshot=True)
        c1.getScreenshot("chat")
        s1.getScreenshot("chat")
        c1.closeActiveChat(confirm=True)
        time.sleep(5)
        s1.closeActiveChat()
        s1.submitQuestionnaire(wait=True)
        c1.submitQuestionnaire(wait=True)
        c1.confirmExit()
        c1.waitForTitle("Einde")
        c1.close()
        s1.closeActiveChat()
        s1.waitForTitle("Sitebeheer | Django site beheerder")
        s1.close()

def test_standard_staff_initiates():
    """Standard chat, staff first to open the chat, so no queue
       for the client, staff to initiate exit."""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick("testbrowser")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    assert type(s1.getClientFormId()) == int
    typing_notification_check(c1, s1)
    typing_notification_check(s1, c1)
    for x in range(15):
        c1.waitForChatLine(s1.sendChatLine())
        s1.waitForChatLine(c1.sendChatLine())
    typing_notification_check(c1, s1)
    typing_notification_check(s1, c1)
    s1.closeActiveChat(confirm=True)
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    c1.submitQuestionnaire(wait=True)
    c1.closeActiveChat()
    c1.waitForTitle("Einde")
    c1.close()

def test_standard_chat_client_initiates():
    """Standard chat, staff opens the staff groupchat, then the
       client enters into the waiting queue. Client to initiate
       exit."""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick("testbrowser")
    c1.submitQuestionnaire(wait=True)
    assert c1.getQueuePos() == 1
    s1.openCarechat()
    s1.waitForClient()
    c1.waitForChat()
    assert type(s1.getClientFormId()) == int
    typing_notification_check(c1, s1)
    typing_notification_check(s1, c1)
    for x in range(15):
        c1.waitForChatLine(s1.sendChatLine())
        s1.waitForChatLine(c1.sendChatLine())
    typing_notification_check(c1, s1)
    typing_notification_check(s1, c1)
    c1.closeActiveChat(confirm=True)
    c1.submitQuestionnaire(wait=True)
    c1.confirmExit()
    c1.waitForTitle("Einde")
    c1.close()
    s1.closeActiveChat()
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()

def test_nickname_collision():
    """Is it handled correctly when the client has the same nick
    as the staff?"""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick(s1.getOwnNick())
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    assert s1.getOwnNick()+"_" == s1.getPeerNick()
    s1.close()
    c1.close()

def test_closed():
    """Is the client redirected correctly when no staff is present?"""
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.waitForTitle("Gesloten")
    c1.close()

def test_staff_priority():
    """Gets a prioriteze staff the chats first?"""
    sN = StaffBrowser(firefoxPlugins=firefoxPlugins)
    sN.login(0)
    sN.openGroupchat()
    sN.openCarechat()
    sP = StaffBrowser(firefoxPlugins=firefoxPlugins)
    sP.login(0, highPriority=True)
    sP.openGroupchat()
    sP.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick("testbrowser")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    sP.waitForClient()
    c1.close()
    sN.close()
    sP.close()
    
def test_linear_queue():
    """Check if queue gets handled ok, when it is nice and neat"""
    x = StatusBrowser(firefoxPlugins=firefoxPlugins)
    assert x.getStatus() == (False, 0)
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    assert x.getStatus() == (False, 0)
    s1.openGroupchat()
    assert x.getStatus() == (True, 0)
    client = []
    for n in range(10):
        c = ClientBrowser(firefoxPlugins=firefoxPlugins)
        c.start()
        c.enterNick("queuetest_"+str(n))
        c.submitQuestionnaire()
        assert c.getQueuePos() == n+1
        assert x.getStatus() == (True, 0)
        client.append(c)
    while client:
        s1.openCarechat()
        s1.waitForClient()
        client[0].waitForChat()
        client[0].waitForChatLine(s1.sendChatLine())
        assert x.getStatus() == (True, 1)
        client[0].closeActiveChat(confirm=True)
        client[0].submitQuestionnaire(wait=True)
        client[0].confirmExit()
        client[0].waitForTitle("Einde")
        client[0].close()
        del client[0]
        s1.closeActiveChat()
        s1.submitQuestionnaire(wait=True)
        assert x.getStatus() == (True, 0)
        for n in range(len(client)):
            assert client[n].getQueuePos() == n+1
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    x.close()

def test_messy_queue():
    """Check if queue gets handled ok when things get messy"""
    x = StatusBrowser(firefoxPlugins=firefoxPlugins)
    assert x.getStatus() == (False, 0)
    staff = []
    client = []
    for n in range(5):
        s = StaffBrowser(firefoxPlugins=firefoxPlugins)
        s.login(user=n)
        staff.append(s)
    for n in range(5):
        client.append(ClientBrowser(firefoxPlugins=firefoxPlugins))
    assert x.getStatus() == (False, 0)
    staff[0].openGroupchat()
    assert x.getStatus() == (True, 0)
    for n in range(3):
        client[n].start()
        client[n].enterNick("queuetest_"+str(n))
        client[n].submitQuestionnaire()
        assert client[n].getQueuePos() == n+1
    assert x.getStatus() == (True, 0)
    staff[1].openGroupchat()
    staff[1].openCarechat()
    staff[1].waitForClient()
    client[0].waitForChat()
    assert x.getStatus() == (True, 1)
    client[0].waitForChatLine(staff[1].sendChatLine())
    staff[0].openCarechat()
    staff[0].waitForClient()
    client[1].waitForChat()
    assert x.getStatus() == (True, 2)
    client[1].waitForChatLine(staff[0].sendChatLine())
    client[3].start()
    client[3].enterNick("queuetest_3")
    client[3].submitQuestionnaire()
    assert client[3].getQueuePos() == 2
    for n in [2, 3, 4]:
        staff[n].openGroupchat()
    assert x.getStatus() == (True, 2)
    for n in [2, 3]:
        staff[n].openCarechat()
        staff[n].waitForClient()
        client[n].waitForChat()
        assert x.getStatus() == (True, n+1)
        client[n].waitForChatLine(staff[n].sendChatLine())
    staff[4].openCarechat()
    client[4].start()
    client[4].enterNick("queuetest_4")
    client[4].submitQuestionnaire()
    staff[4].waitForClient()
    client[4].waitForChat()
    assert x.getStatus() == (True, 5)
    client[4].waitForChatLine(staff[4].sendChatLine())
    staff[0].closeActiveChat(confirm=True)
    staff[0].submitQuestionnaire(wait=True)
    client[1].submitQuestionnaire(wait=True)
    client[1].closeActiveChat()
    client[1].waitForTitle("Einde")
    assert x.getStatus() == (True, 4)
    staff[0].openCarechat()
    client[1].start()
    client[1].enterNick("queuetest_1bis")
    client[1].submitQuestionnaire()
    staff[0].waitForClient()
    client[1].waitForChat()
    assert x.getStatus() == (True, 5)
    client[1].waitForChatLine(staff[0].sendChatLine())
    for n in range(5):
        client[n].close()
        staff[n].close()
    x.close()

def test_staff_groupchat():
    """Can we communicat in the group chat?"""
    staff=[]
    for n in range(5):
        s = StaffBrowser(firefoxPlugins=firefoxPlugins)
        s.login(user=n)
        s.openGroupchat()
        staff.append(s)
    for m in range(10):
        for n in range(len(staff)):
            line=staff[n].sendChatLine()
            for o in range(len(staff)):
                staff[o].waitForChatLine(line)
    for n in range(len(staff)):
        staff[n].close()

def test_fast_chat_lines():
    """How fast can we go?"""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick("testbrowser")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    for x in range(100):
        s1.sendChatLine("a")
    s1.waitForChatLine(c1.sendChatLine())
    s1.closeActiveChat(confirm=True)
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    c1.submitQuestionnaire(wait=True)
    c1.closeActiveChat()
    c1.waitForTitle("Einde")
    c1.close()

def test_non_ascii_nick():
    """Does the bot handle non-ascii nicknames ok?"""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick(u"þessað")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    c1.waitForChatLine(s1.sendChatLine())
    s1.closeActiveChat(confirm=True)
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    time.sleep(120)
    c1.submitQuestionnaire(wait=True)
    c1.closeActiveChat()
    c1.waitForTitle("Einde")
    c1.close()
     
def test_idle_nickname():
    """What happens if you wait log before... entering a nickname"""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    time.sleep(30*60)
    c1.enterNick(u"testbrowser")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    c1.waitForChatLine(s1.sendChatLine())
    s1.closeActiveChat(confirm=True)
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    c1.submitQuestionnaire(wait=True)
    c1.closeActiveChat()
    c1.waitForTitle("Einde")
    c1.close()

def test_idle_available():
    """What happens if you wait log before... somebody enters"""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    time.sleep(4*60*60)
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick(u"testbrowser")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    c1.waitForChatLine(s1.sendChatLine())
    s1.closeActiveChat(confirm=True)
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    c1.submitQuestionnaire(wait=True)
    c1.closeActiveChat()
    c1.waitForTitle("Einde")
    c1.close()

def test_idle_chat():
    """What happens if you wait log before... entering the next chatline"""
    s1 = StaffBrowser(firefoxPlugins=firefoxPlugins)
    s1.login(0)
    s1.openGroupchat()
    s1.openCarechat()
    c1 = ClientBrowser(firefoxPlugins=firefoxPlugins)
    c1.start()
    c1.enterNick(u"testbrowser")
    c1.submitQuestionnaire(wait=True)
    c1.waitForChat()
    s1.waitForClient()
    c1.waitForChatLine(s1.sendChatLine())
    time.sleep(2*60*60)
    c1.waitForChatLine(s1.sendChatLine())
    s1.closeActiveChat(confirm=True)
    s1.submitQuestionnaire(wait=True)
    s1.closeActiveChat()
    s1.waitForTitle("Sitebeheer | Django site beheerder")
    s1.close()
    c1.submitQuestionnaire(wait=True)
    c1.closeActiveChat()
    c1.waitForTitle("Einde")
    c1.close()
