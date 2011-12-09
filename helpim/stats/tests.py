from django.contrib.auth.models import User
from django.core.urlresolvers import resolve, Resolver404
from django.test import TestCase
from django.test.client import Client

class UrlPatternsTestCase(TestCase):
    '''Test url design of stats app'''
    
    # base url where stats app runs
    base_url = "/admin/stats/"

    def setUp(self):
        super(UrlPatternsTestCase, self).setUp()

        self.c = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'test')
        self.assertTrue(self.c.login(username=self.user.username, password='test'), 'Could not login')


    def _assertUrlMapping(self, url, action, params={}):
        response = self.c.get(self.base_url + url, follow=True)
        self.assertTrue(response.status_code != 404, 'URL not found')

        try:
            info = resolve(response.request["PATH_INFO"])
        except Resolver404:
            self.fail("Could not resolve '%s'" % (response.request["PATH_INFO"]))

        self.assertEqual(info.url_name, action, "view name is '%s', but '%s' was expected" % (info.url_name, action))
        self.assertEqual(len(info.kwargs), len(params), 'Number of parameters does not match: expected: %s -- got: %s' % (params, info.kwargs))

        for key, value in params.items():
            self.assertTrue(key in info.kwargs, 'Expected parameter %s not found' % (key))
            self.assertEqual(info.kwargs[key], value, 'Values for parameter %s do not match' % key)


    def testStatsUrlMappings(self):
        self._assertUrlMapping('', 'stats_index')

        self._assertUrlMapping('chat', 'stats_overview', {'keyword': 'chat'})
        self._assertUrlMapping('chat/', 'stats_overview', {'keyword': 'chat'})

        self._assertUrlMapping('chat/1999', 'stats_overview', {'keyword': 'chat', 'year': '1999'})
        self._assertUrlMapping('chat/1999/', 'stats_overview', {'keyword': 'chat', 'year': '1999'})

        self._assertUrlMapping('chat/2011/csv', 'stats_overview', {'keyword': 'chat', 'year': '2011', 'format': 'csv'})
        self._assertUrlMapping('chat/2011/csv/', 'stats_overview', {'keyword': 'chat', 'year': '2011', 'format': 'csv'})

        self.assertRaisesRegexp(AssertionError, 'URL not found',
                                lambda: self._assertUrlMapping('keyworddoesntexist', 'stats_overview'))

