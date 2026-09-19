# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import RequestFactory, SimpleTestCase

from api import views

class InvalidTtlTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_create_rejects_non_integer_ttl(self):
        request = self.factory.post('/create/', {'ttl': 'not-a-number'})
        request.META['HTTP_HOST'] = 'example.test'

        response = views.create(request)

        self.assertEqual(response.status_code, 400)

    def test_refresh_rejects_non_integer_ttl(self):
        request = self.factory.post('/i/example/refresh/', {'ttl': 'not-a-number'})

        response = views.refresh(request, 'example')

        self.assertEqual(response.status_code, 400)
