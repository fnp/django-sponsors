from django.core.files.base import ContentFile
from django.test import TestCase
from sponsors.models import Sponsor, SponsorPage
from PIL import Image

try:
    from io import BytesIO
except ImportError:
    # Python 2
    from StringIO import StringIO as BytesIO


class SponsorsTest(TestCase):
    def test_empty_page(self):
        page = SponsorPage(name='test')
        page.save()

    def test_simple_sponsor(self):
        s = Sponsor(name='Test Sponsor')
        im = Image.new('1', (1,1))
        b = BytesIO()
        im.save(b, 'PNG')
        s.logo.save('test.png', ContentFile(b.getvalue()), save=True)

        page = SponsorPage(
            name='Sponsor',
            sponsors=[
                {"name": "empty-column", "sponsors": []},
                {"name": "test-column", "sponsors": [s.id]},
            ])
        page.save()
        self.assertNotIn('empty-column', page._html)
        self.assertIn('test-column', page._html)
        self.assertIn('Test Sponsor', page._html)

