# -*- coding: utf-8 -*-
# This file is part of django-sponsors, licensed under GNU Affero GPLv3 or later.
# Copyright © Fundacja Nowoczesna Polska. See NOTICE for more information.
#
import time
from StringIO import StringIO
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from PIL import Image

from jsonfield import JSONField
from django.core.files.base import ContentFile

THUMB_WIDTH = getattr(settings, 'SPONSORS_THUMB_WIDTH', 120)
THUMB_HEIGHT = getattr(settings, 'SPONSORS_THUMB_HEIGHT', 120)


class Sponsor(models.Model):
    name = models.CharField(_('name'), max_length=120)
    _description = models.CharField(_('description'), blank=True, max_length=255)
    logo = models.ImageField(_('logo'), upload_to='sponsorzy/sponsor/logo')
    url = models.URLField(_('url'), blank=True, verify_exists=False)

    def __unicode__(self):
        return self.name

    def description(self):
        if len(self._description):
            return self._description
        else:
            return self.name

    def size(self):
        width, height = THUMB_WIDTH, THUMB_HEIGHT
        if width is None:
            simg = Image.open(self.logo.path)
            width = int(float(simg.size[0]) / simg.size[1] * height)
        elif height is None:
            simg = Image.open(self.logo.path)
            height = int(float(simg.size[1]) / simg.size[0] * width)
        return width, height


class SponsorPage(models.Model):
    name = models.CharField(_('name'), max_length=120)
    sponsors = JSONField(_('sponsors'), default={})
    _html = models.TextField(blank=True, editable=False)
    sprite = models.ImageField(upload_to='sponsorzy/sprite', blank=True)

    def populated_sponsors(self):
        result = []
        offset = 0
        for column in self.sponsors:
            result_group = {'name': column['name'], 'sponsors': []}
            sponsor_objects = Sponsor.objects.in_bulk(column['sponsors'])
            for sponsor_pk in column['sponsors']:
                try:
                    sponsor = sponsor_objects[sponsor_pk]
                except KeyError:
                    pass
                else:
                    result_group['sponsors'].append((offset, sponsor))
                    offset -= sponsor.size()[1]
            result.append(result_group)
        return result

    def render_sprite(self):
        sponsor_ids = []
        for column in self.sponsors:
            sponsor_ids.extend(column['sponsors'])
        sponsors = Sponsor.objects.in_bulk(sponsor_ids)
        total_width = 0
        total_height = 0
        for sponsor in sponsors.values():
            w, h = sponsor.size()
            total_width = max(total_width, w)
            total_height += h
        sprite = Image.new('RGBA', (total_width, total_height))
        offset = 0
        for i, sponsor_id in enumerate(sponsor_ids):
            sponsor = sponsors[sponsor_id]
            simg = Image.open(sponsor.logo.path)
            thumb_size = sponsor.size()
            # FIXME: This is too complicated now.
            if simg.size[0] > thumb_size[0] or simg.size[1] > thumb_size[1]:
                size = (
                    min(thumb_size[0], 
                        simg.size[0] * thumb_size[1] / simg.size[1]),
                    min(thumb_size[1],
                        simg.size[1] * thumb_size[0] / simg.size[0])
                )
                simg = simg.resize(size, Image.ANTIALIAS)
            sprite.paste(simg, (
                    (thumb_size[0] - simg.size[0]) / 2,
                    offset + (thumb_size[1] - simg.size[1]) / 2,
                    ))
            offset += thumb_size[1]
        imgstr = StringIO()
        sprite.save(imgstr, 'png')

        if self.sprite:
            self.sprite.delete(save=False)
        self.sprite.save('sponsorzy/sprite/%s-%d.png' % (self.name, time.time()), ContentFile(imgstr.getvalue()), save=False)

    def html(self):
        return self._html
    html = property(fget=html)

    def save(self, *args, **kwargs):
        self.render_sprite()
        self._html = render_to_string('sponsors/page.html', {
            'sponsors': self.populated_sponsors(),
            'page': self,
        })
        return super(SponsorPage, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

