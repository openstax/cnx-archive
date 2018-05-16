# Based largely on  werkzeug.contrib.sitemap (PR)
"""This module prvides a class called :class:`Sitemap` for web sitemaps.

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

import datetime

from lxml import etree


SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class SitemapIndex(object):
    """A helper class that creates sitemap_index.xml."""

    def __init__(self, sitemaps=None):
        self.sitemaps = sitemaps and list(sitemaps) or []
        for sitemap in self.sitemaps:
            if not sitemap.url:
                raise ValueError('sitemap url must be set')

    def to_string(self):
        """Convert SitemapIndex into a string."""
        root = etree.Element('sitemapindex', nsmap={None: SITEMAP_NS})
        for sitemap in self.sitemaps:
            sm = etree.SubElement(root, 'sitemap')
            etree.SubElement(sm, 'loc').text = sitemap.url
            if hasattr(sitemap.lastmod, 'strftime'):
                etree.SubElement(sm, 'lastmod').text = \
                    sitemap.lastmod.strftime('%Y-%m-%d')
            elif isinstance(sitemap.lastmod, str):
                etree.SubElement(sm, 'lastmod').text = sitemap.lastmod
        return etree.tostring(root, pretty_print=True, xml_declaration=True,
                              encoding='utf-8')

    def __call__(self):
        """Return the string."""
        return self.__str__()

    def __unicode__(self):
        """Return the string."""
        return self.to_string()

    def __str__(self):
        """Return the string."""
        return self.to_string().encode('utf-8')


class Sitemap(object):
    """A helper class that creates sitemap.xml."""

    def __init__(self, urls=None, lastmod=None, url=None):
        """Build sitemap from urls."""
        self.urls = urls and list(urls) or []
        self.lastmod = lastmod or \
            datetime.datetime.utcnow().strftime('%Y-%m-%d')
        self.url = url

    def add_url(self, *args, **kwargs):
        """Add a new url to the sitemap.

        This function can either be called with a :class:`UrlEntry`
        or some keyword and positional arguments that are forwarded to
        the :class:`UrlEntry` constructor.
        """
        if len(args) == 1 and not kwargs and isinstance(args[0], UrlEntry):
            self.urls.append(args[0])
        else:
            self.urls.append(UrlEntry(*args, **kwargs))

    def __repr__(self):
        """Simple string representation."""
        return '<%s (%d entrie(s))>' % (
            self.__class__.__name__,
            len(self.urls)
        )

    def to_string(self):
        """Convert the sitemap into a string."""
        root = etree.Element('urlset', nsmap={None: SITEMAP_NS})
        for url in self.urls:
            url.generate(root)
        return etree.tostring(root, pretty_print=True, xml_declaration=True,
                              encoding='utf-8')

    def __call__(self):
        """Return the string."""
        return self.__str__()

    def __unicode__(self):
        """Return the string."""
        return self.to_string()

    def __str__(self):
        """Return the string."""
        return self.to_string().encode('utf-8')


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
        """Create a URLEntry object for sitemap."""
        self.loc = loc
        self.lastmod = kwargs.get('lastmod')
        self.changefreq = kwargs.get('changefreq')
        if self.changefreq and self.changefreq not in self.freq_values:
            raise ValueError('changefreq must be one of %s' %
                             (', '.join(self.freq_values)))
        self.priority = kwargs.get('priority')
        if self.priority and self.priority < 0.0 or self.priority > 1.0:
            raise ValueError('priority must be between 0.0 and 1.0')

        if self.loc is None:
            raise ValueError('location is required')

    def __repr__(self):
        """Some useful info."""
        return '<%s %r>' % (
            self.__class__.__name__,
            self.loc
        )

    def generate(self, root_element=None):
        """Create <url> element under root_element."""
        if root_element is not None:
            url = etree.SubElement(root_element, 'url')
        else:
            url = etree.Element('url')
        etree.SubElement(url, 'loc').text = self.loc
        if self.lastmod:
            if hasattr(self.lastmod, 'strftime'):
                etree.SubElement(url, 'lastmod').text = \
                    self.lastmod.strftime('%Y-%m-%d')
            elif isinstance(self.lastmod, str):
                etree.SubElement(url, 'lastmod').text = self.lastmod
        if self.changefreq and self.changefreq in self.freq_values:
            etree.SubElement(url, 'changefreq').text = self.changefreq
        if self.priority and 0.0 <= self.priority <= 1.0:
            etree.SubElement(url, 'priority').text = str(self.priority)
        return url

    def to_string(self):
        """Convert the url item into a unicode object."""
        return etree.tostring(self.generate(), pretty_print=True)

    def __unicode__(self):
        """Return the string."""
        return self.to_string()

    def __str__(self):
        """Return the string."""
        return self.to_string().encode('utf-8')
