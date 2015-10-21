# Based largely on  werkzeug.contrib.sitemap (PR)
"""    ~~~~~~~~~~~~~~~~~~~~~~~~

    This module provides a class called :class:`Sitemap` which can be used to
    generate sitemap.xml in the sitemap XML format. For more information
    please refer to http://sitemaps.org/protocol.html.

    Example::

        def sitemap():
            xml = Sitemap()

            for post in Post.query.limit(10).all():
                xml.add_url(post.url, lastmod=post.last_update,
                        changefreq='weekly', priority=0.8)

            return xml.get_response()
"""
from __future__ import unicode_literals
from datetime import datetime

from . import IS_PY2
from .utils import escape

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class Sitemap(object):
    """A helper class that creates sitemap.xml."""

    def __init__(self, urls=None):
        self.urls = urls and list(urls) or []

    def add_url(self, *args, **kwargs):
        """Add a new url to the sitemap. This function can either be called
        with a :class:`UrlEntry` or some keyword and positional arguments that
        are forwarded to the :class:`UrlEntry` constructor.
        """
        if len(args) == 1 and not kwargs and isinstance(args[0], UrlEntry):
            self.urls.append(args[0])
        else:
            self.urls.append(UrlEntry(*args, **kwargs))

    def __repr__(self):
        return '<%s (%d entrie(s))>' % (
            self.__class__.__name__,
            len(self.urls)
        )

    def generate(self):
        """Return a generate that yields pieces of XML."""
        yield '<?xml version="1.0" encoding="utf-8"?>\n'
        yield '<urlset xmlns="%s">\n' % SITEMAP_NS
        for url in self.urls:
            for line in url.generate():
                yield '  ' + line
        yield '</urlset>\n'

    def to_string(self):
        """Convert the sitemap into a string."""
        return ''.join(self.generate())

    def __call__(self):
        return self.__str__()

    def __unicode__(self):
        # FIXME remove when we no longer need to support python 2
        return self.to_string()

    def __bytes__(self):
        return self.to_string().encode('utf-8')

    def __str__(self):
        if IS_PY2:
            return self.to_string().encode('utf-8')
        return self.to_string()


class UrlEntry(object):
    """Represents a single url entry in the sitemap.

    :param loc: the localtion of the url. Required.
    :param lastmod: the time the url was modified the last time. Must be a
    :class:`datetime.datetime` object or a string representing the time in
    ISO format, %Y-%m-%dT%H:%M:%S%z.
    :param changefreq: how frequently the content of the url is likely to
    change. One of ``'always'``, ``'hourly'``, ``'daily'``, ``'weekly'``,
    ``'monthly'``, ``'yearly'``, ``'never'``.
    :param priority: the priority of this url relative to the other urls on
    your site. Valid values from 0.0 to 1.0.
    """

    freq_values = [
        'always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never']

    def __init__(self, loc=None, **kwargs):
        self.loc = loc
        self.lastmod = kwargs.get('lastmod')
        self.changefreq = kwargs.get('changefreq')
        if self.changefreq and self.changefreq not in self.freq_values:
            raise ValueError('changefreq must be one of %s' %
                             (', '.join(self.freq_values)))
        self.priority = kwargs.get('priority')
        if self.priority and (self.priority < 0.0 or self.priority > 1.0):
            raise ValueError('priority must be between 0.0 and 1.0')

        if self.loc is None:
            raise ValueError('location is required')

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.loc
        )

    def generate(self):
        """Yields pieces of XML."""
        yield '<url>\n'
        yield '<loc>%s</loc>\n' % escape(self.loc)
        if self.lastmod:
            if hasattr(self.lastmod, 'strftime'):
                yield '<lastmod>%s</lastmod>\n' % \
                    self.lastmod.strftime('%Y-%m-%d')
            elif (IS_PY2 and isinstance(self.lastmod, basestring) or
                  not IS_PY2 and isinstance(self.lastmod, (bytes, str))):
                yield '<lastmod>%s</lastmod>\n' % self.lastmod
        if self.changefreq and self.changefreq in self.freq_values:
            yield '<changefreq>%s</changefreq>\n' % self.changefreq
        if self.priority and 0.0 <= self.priority <= 1.0:
            yield '<priority>%s</priority>\n' % self.priority
        yield '</url>\n'

    def to_string(self):
        """Convert the url item into a unicode object."""
        return ''.join(self.generate())

    def __unicode__(self):
        # FIXME remove when we no longer need to support python 2
        return self.to_string()

    def __bytes__(self):
        return self.to_string().encode('utf-8')

    def __str__(self):
        if IS_PY2:
            return self.to_string().encode('utf-8')
        return self.to_string()
