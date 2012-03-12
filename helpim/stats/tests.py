from datetime import date

from django.contrib.auth.models import ContentType, Permission, User
from django.core.urlresolvers import resolve, Resolver404, reverse
from django.test import TestCase
from django.test.client import Client
from django.utils.translation import ugettext as _

from helpim.common.models import BranchOffice
from helpim.conversations.models import Chat
from helpim.stats.models import BranchReportVariable, DurationReportVariable, NoneReportVariable, Report, ReportVariable, WeekdayReportVariable


class UrlPatternsTestCase(TestCase):
    '''Test url design of stats app'''

    # base url where stats app runs
    base_url = "/admin/stats/"

    def setUp(self):
        super(UrlPatternsTestCase, self).setUp()

        self.c = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'test')
        c, created = ContentType.objects.get_or_create(model='', app_label='stats',
                                                       defaults={'name': 'stats'})
        p, created = Permission.objects.get_or_create(codename='can_view_stats', content_type=c,
                                                      defaults={'name': 'Can view Stats', 'content_type': c})
        self.user.user_permissions.add(p)
        self.assertTrue(self.c.login(username=self.user.username, password='test'), 'Could not login')


    def _assertUrlMapping(self, url, action, params={}, follow=True):
        '''assert that when `url` is accessed, the view `action` is invoked with parameters dictionary `params`'''

        response = self.c.get(self.base_url + url, follow=follow)
        self.assertTrue(response.status_code != 404, 'URL not found')

        try:
            info = resolve(response.request["PATH_INFO"])
        except Resolver404:
            self.fail("Could not resolve '%s'" % (response.request["PATH_INFO"]))

        self.assertEqual(info.url_name, action, "view name is '%s', but '%s' was expected" % (info.url_name, action))
        self.assertEqual(len(info.kwargs), len(params), 'Number of parameters does not match: expected: %s -- got: %s' % (params, info.kwargs))

        for key, value in params.items():
            self.assertTrue(key in info.kwargs, 'Expected parameter "%s" not found' % (key))
            self.assertEqual(info.kwargs[key], value, 'Values for parameter "%s" do not match: "%s" != "%s"' % (key, info.kwargs[key], value))


    def testStatsUrlMappings(self):
        '''test url mappings for general stats functionality'''

        self._assertUrlMapping('', 'stats_index')

        self._assertUrlMapping('chat', 'stats_overview', {'keyword': 'chat'})
        self._assertUrlMapping('chat/', 'stats_overview', {'keyword': 'chat'})

        self._assertUrlMapping('chat/1999', 'stats_overview', {'keyword': 'chat', 'year': '1999'})
        self._assertUrlMapping('chat/1999/', 'stats_overview', {'keyword': 'chat', 'year': '1999'})

        self._assertUrlMapping('chat/2011/csv', 'stats_overview', {'keyword': 'chat', 'year': '2011', 'format': 'csv'})
        self._assertUrlMapping('chat/2011/csv/', 'stats_overview', {'keyword': 'chat', 'year': '2011', 'format': 'csv'})

        self.assertRaisesRegexp(AssertionError, 'URL not found',
                                lambda: self._assertUrlMapping('keyworddoesntexist', 'stats_overview'))


    def testReportsUrlMappings(self):
        '''test url mappings for reports functionality'''

        # create Report with specific id to be used throughout test
        r = Report(period_start=date(2000, 1, 1), period_end=date(2000, 1, 1), variable1='weekday', variable2='branch')
        r.save()
        r.id = 4143
        r.save()

        self._assertUrlMapping('reports/new/', 'report_new')
        self._assertUrlMapping('reports/4143/', 'report_show', {'id': '4143'})
        self._assertUrlMapping('reports/4143/edit/', 'report_edit', {'id': '4143'})
        self._assertUrlMapping('reports/4143/delete/', 'report_delete', {'id': '4143'}, follow=False)


    def testPermission(self):
        # access allowed for privileged user
        response = self.c.get(reverse('stats_index'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stats/stats_index.html')


        # test access to stats with unprivileged user
        self.c = Client()
        unprivilegedUser = User.objects.create_user('bob', 'me@bob.com', 'bob')
        self.assertTrue(self.c.login(username=unprivilegedUser.username, password='bob'), 'Bob could not login')

        response = self.c.get(reverse('stats_index'))
        self.assertNotEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, 'stats/stats_index.html')


class ReportTestCase(TestCase):
    fixtures = ['reports-test.json']

    def test_matching_chats(self):
        r = Report.objects.get(pk=1)
        r.period_start = date(2010, 1, 1)
        r.period_end = date(2010, 1, 1)

        chats = r.matching_chats()
        self.assertItemsEqual(Chat.objects.filter(id__in=[1]), chats)

        # remove lower bound
        r.period_start = None
        chats = r.matching_chats()
        self.assertItemsEqual(Chat.objects.filter(id__in=[1, 2]), chats)

        # remove upper bound
        r.period_end = None
        chats = r.matching_chats()
        self.assertItemsEqual(Chat.objects.all(), chats)

        # set careworker only
        r.careworker = User.objects.get(pk=55)
        chats = r.matching_chats()
        self.assertItemsEqual(Chat.objects.filter(id__in=[2]), chats)

        # set branch office only
        r.careworker = None
        r.branch = BranchOffice.objects.get(pk=1)
        chats = r.matching_chats()
        self.assertItemsEqual(Chat.objects.filter(id__in=[2, 3]), chats)

        # set branch and careworker
        r.careworker = User.objects.get(pk=22)
        chats = r.matching_chats()
        self.assertItemsEqual(Chat.objects.filter(id__in=[3]), chats)

    def test_generate_2variables(self):
        r = Report.objects.get(pk=1)

        data = r.generate()['rendered_report']
        self.assertTrue(len(data) > 0)

        # determine number of cells
        cells = 0
        for col in data.iterkeys():
            for cell in data[col].iterkeys():
                cells += 1

        # +1 for 'Total' column
        var1_samples = list(ReportVariable.find_variable(r.variable1).values())
        var2_samples = list(ReportVariable.find_variable(r.variable2).values())
        self.assertEqual((len(var1_samples) + 1) * (len(var2_samples) + 1), cells)

        # cells
        self.assertEqual(1, data[_('Thursday')]['Office Amsterdam'])
        self.assertEqual(1, data[_('Friday')][Report.OTHER_COLUMN])
        self.assertEqual(1, data[_('Saturday')]['Office Amsterdam'])

        # row sums
        self.assertEqual(2, data[Report.TOTAL_COLUMN]['Office Amsterdam'])
        self.assertEqual(1, data[Report.TOTAL_COLUMN][Report.OTHER_COLUMN])

        # col sums
        self.assertEqual(1, data[_('Thursday')][Report.TOTAL_COLUMN])
        self.assertEqual(1, data[_('Friday')][Report.TOTAL_COLUMN])
        self.assertEqual(1, data[_('Saturday')][Report.TOTAL_COLUMN])

        # table sum
        self.assertEqual(3, data[Report.TOTAL_COLUMN][Report.TOTAL_COLUMN])

    def test_generate_1variable(self):
        r = Report.objects.get(pk=1)

        # remove variable2
        r.variable2 = NoneReportVariable.get_choices_tuple()[0]

        data = r.generate()['rendered_report']
        self.assertTrue(len(data) > 0)

        # determine number of cells
        cells = 0
        for col in data.iterkeys():
            for cell in data[col].iterkeys():
                cells += 1

        # +1 for 'Total' column
        var1_samples = list(ReportVariable.find_variable(r.variable1).values())
        var2_samples = list(ReportVariable.find_variable(r.variable2).values())
        self.assertEqual((len(var1_samples) + 1) * (len(var2_samples) + 1), cells)

        # cells
        self.assertEqual(1, data[_('Thursday')][NoneReportVariable.EMPTY])
        self.assertEqual(1, data[_('Friday')][NoneReportVariable.EMPTY])
        self.assertEqual(1, data[_('Saturday')][NoneReportVariable.EMPTY])

        # row sums
        self.assertEqual(3, data[Report.TOTAL_COLUMN][NoneReportVariable.EMPTY])

        # col sums
        self.assertEqual(1, data[_('Thursday')][Report.TOTAL_COLUMN])
        self.assertEqual(1, data[_('Friday')][Report.TOTAL_COLUMN])
        self.assertEqual(1, data[_('Saturday')][Report.TOTAL_COLUMN])

        # table sum
        self.assertEqual(3, data[Report.TOTAL_COLUMN][Report.TOTAL_COLUMN])

    def test_generate_0variables(self):
        r = Report.objects.get(pk=1)

        # remove both variables
        r.variable1 = NoneReportVariable.get_choices_tuple()[0]
        r.variable2 = NoneReportVariable.get_choices_tuple()[0]

        data = r.generate()['rendered_report']
        self.assertTrue(len(data) > 0)

        # determine number of cells
        cells = 0
        for col in data.iterkeys():
            for cell in data[col].iterkeys():
                cells += 1

        # +1 for 'Total' column
        var1_samples = list(ReportVariable.find_variable(r.variable1).values())
        var2_samples = list(ReportVariable.find_variable(r.variable2).values())
        self.assertEqual((len(var1_samples) + 1) * (len(var2_samples) + 1), cells)

        # cells
        self.assertEqual(3, data[NoneReportVariable.EMPTY][NoneReportVariable.EMPTY])

        # row/col/table sums
        self.assertEqual(3, data[Report.TOTAL_COLUMN][NoneReportVariable.EMPTY])
        self.assertEqual(3, data[NoneReportVariable.EMPTY][Report.TOTAL_COLUMN])
        self.assertEqual(3, data[Report.TOTAL_COLUMN][Report.TOTAL_COLUMN])

    def test_generate_0variables_unique(self):
        r = Report.objects.get(pk=1)
        r.variable1 = NoneReportVariable.get_choices_tuple()[0]
        r.variable2 = NoneReportVariable.get_choices_tuple()[0]
        r.output = 'unique'

        data = r.generate()['rendered_report']
        self.assertTrue(len(data) > 0)

        # cells
        self.assertEqual(2, data[NoneReportVariable.EMPTY][NoneReportVariable.EMPTY])

        # row/col/table sums
        self.assertEqual(2, data[Report.TOTAL_COLUMN][NoneReportVariable.EMPTY])
        self.assertEqual(2, data[NoneReportVariable.EMPTY][Report.TOTAL_COLUMN])
        self.assertEqual(2, data[Report.TOTAL_COLUMN][Report.TOTAL_COLUMN])

class ReportVariableTestCase(TestCase):
    def setUp(self):
        super(ReportVariableTestCase, self).setUp()

        ReportVariable.all_variables()

    def test_register_variable(self):
        # clear state, might have been set by previous tests
        ReportVariable.known_variables = {}

        self.assertEqual(0, len(ReportVariable.known_variables), "No variables should be registered")

        # calling all_variables() triggers auto-discovery and addition of variables
        self.assertTrue(WeekdayReportVariable in ReportVariable.all_variables(), "Weekday variable should be registered")
        self.assertTrue(len(ReportVariable.known_variables) > 0, "No variables should be registered")

    def test_find(self):
        self.assertEqual(WeekdayReportVariable, ReportVariable.find_variable('weekday'))
        self.assertEqual(('weekday', _('Weekday')), ReportVariable.find_variable('weekday').get_choices_tuple())

        self.assertEqual(NoneReportVariable, ReportVariable.find_variable('doesntexist'))
        self.assertEqual(NoneReportVariable, ReportVariable.find_variable(None))


class WeekdayReportVariableTestCase(TestCase):
    fixtures = ['reports-test.json']

    def test_values(self):
        # 7 weekdays, +1 for Other/No value
        self.assertEqual(7 + 1, len(WeekdayReportVariable.values()))

    def test_extract(self):
        c1 = Chat.objects.get(pk=1)
        c2 = Chat.objects.get(pk=2)
        c3 = Chat.objects.get(pk=3)

        self.assertEqual(_('Friday'), WeekdayReportVariable.extract_value(c1))
        self.assertEqual(_('Thursday'), WeekdayReportVariable.extract_value(c2))
        self.assertEqual(_('Saturday'), WeekdayReportVariable.extract_value(c3))

class BranchReportVariableTestCase(TestCase):
    fixtures = ['reports-test.json']

    def test_values(self):
        # +1 for Other/No value
        self.assertEqual(len(BranchOffice.objects.all()) + 1, len(list(BranchReportVariable.values())))

        self.assertTrue('Office Amsterdam' in BranchReportVariable.values())
        self.assertTrue('Office Rotterdam' in BranchReportVariable.values())

    def test_extract(self):
        c1 = Chat.objects.get(pk=1)
        c2 = Chat.objects.get(pk=2)
        c3 = Chat.objects.get(pk=3)

        self.assertEqual(Report.OTHER_COLUMN, BranchReportVariable.extract_value(c1))
        self.assertEqual('Office Amsterdam', BranchReportVariable.extract_value(c2))
        self.assertEqual('Office Amsterdam', BranchReportVariable.extract_value(c3))

class NoneReportVariableTestCase(TestCase):
    fixtures = ['reports-test.json']

    def test_values(self):
        self.assertEqual(1, len(list(NoneReportVariable.values())))
        self.assertTrue(NoneReportVariable.EMPTY in NoneReportVariable.values())

    def test_extract(self):
        c1 = Chat.objects.get(pk=1)
        c2 = Chat.objects.get(pk=2)
        c3 = Chat.objects.get(pk=3)

        self.assertEqual(NoneReportVariable.EMPTY, NoneReportVariable.extract_value(c1))
        self.assertEqual(NoneReportVariable.EMPTY, NoneReportVariable.extract_value(c2))
        self.assertEqual(NoneReportVariable.EMPTY, NoneReportVariable.extract_value(c3))

class DurationReportVariableTestCase(TestCase):
    fixtures = ['reports-test.json']

    def test_values(self):
        # +1 for Other/No value
        self.assertEqual(6 + 1, len(DurationReportVariable.values()))

    def test_extract(self):
        c1 = Chat.objects.get(pk=1)
        c2 = Chat.objects.get(pk=2)
        c3 = Chat.objects.get(pk=3)

        self.assertEqual(_('0-5'), DurationReportVariable.extract_value(c1))
        self.assertEqual(_('10-15'), DurationReportVariable.extract_value(c2))
        self.assertEqual(_('45+'), DurationReportVariable.extract_value(c3))
