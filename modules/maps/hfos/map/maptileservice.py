"""

Module: TileCache
=================

Autonomously operating local tilecache

:copyright: (C) 2011-2016 riot@c-base.org
:license: GPLv3 (See LICENSE)

"""

import socket
import os
import six
import errno
from circuits import Worker, task
from circuits.web.tools import serve_file
from circuits.web.controllers import Controller
from hfos.logger import hfoslog, error, verbose, warn

if six.PY2:
    from urllib import unquote, urlopen
else:
    from urllib.request import urlopen  # NOQA
    from urllib.parse import unquote  # NOQA

__author__ = "Heiko 'riot' Weinen <riot@c-base.org>"


def get_tile(url):
    """
    Threadable function to retrieve map tiles from the internet
    :param url: URL of tile to get
    """
    log = ""
    connection = None

    try:
        if six.PY3:
            connection = urlopen(url=url, timeout=2)  # NOQA
        else:
            connection = urlopen(url=url)
    except Exception as e:
        log += "MTST: ERROR Tilegetter error: %s " % str([type(e), e, url])

    content = ""

    # Read and return requested content
    if connection:
        try:
            content = connection.read()
        except (socket.timeout, socket.error) as e:
            log += "MTST: ERROR Tilegetter error: %s " % str([type(e), e])

        connection.close()
    else:
        log += "MTST: ERROR Got no connection."

    return content, log


class UrlError(Exception):
    pass


class MaptileService(Controller):
    """
    Threaded, disk-caching tile delivery component
    """
    # channel = "web"

    configprops = {}

    def __init__(self, defaulttile=None, **kwargs):
        """

        :param path: Webserver path to offer cache on
        :param tilepath: Caching directory structure target path
        :param defaulttile: Used, when no tile can be cached
        :param kwargs:
        """
        super(MaptileService, self).__init__(**kwargs)
        self.worker = Worker(process=False, workers=2,
                             channel="tcworkers").register(self)

        self.cachepath = "/var/cache/hfos"
        self.defaulttile = defaulttile
        self._tilelist = []

    def _splitCacheURL(self, url, urltype):
        try:
            # hfoslog('SPLITTING: ', url)
            url = url[len('/' + urltype):].lstrip('/')
            url = unquote(url)

            # hfoslog('SPLITDONE:', url)

            if '..' in url:  # Does this need more safety checks?
                hfoslog("Fishy url with parent path: ", url, lvl=error,
                        emitter="MTS")
                raise UrlError

            spliturl = url.split("/")
            service = "/".join(
                spliturl[0:-3])  # get all but the coords as service
            # hfoslog('SERVICE:', service)

            x = spliturl[-3]
            y = spliturl[-2]
            z = spliturl[-1].split('.')[0]

            filename = os.path.join(self.cachepath, urltype, service, x,
                                    y) + "/" + z + ".png"
            realurl = "http://" + service + "/" + x + "/" + y + "/" + z + \
                      ".png"
        except Exception as e:
            hfoslog("ERROR (%s) in URL: %s" % (e, url), emitter="MTS")
            raise UrlError

        return filename, realurl

    def rastertiles(self, event, *args, **kwargs):
        request, response = event.args[:2]
        try:
            filename, url = self._splitCacheURL(request.path, 'rastertiles')
        except UrlError as e:
            hfoslog('Rastertile cache url error:', e, exc=True, lvl=warn)
            return

        # hfoslog("RASTER QUERY:", filename, lvl=error)
        if os.path.exists(filename):
            return serve_file(request, response, filename)
        else:
            hfoslog('Non-existing raster tile request:', filename, lvl=verbose)

    def tilecache(self, event, *args, **kwargs):
        """Checks and caches a requested tile to disk, then delivers it to
        client"""
        request, response = event.args[:2]
        try:
            filename, url = self._splitCacheURL(request.path, 'tilecache')
        except UrlError:
            return

        # hfoslog('CACHE QUERY:', filename, url)

        # Do we have the tile already?
        if os.path.isfile(filename):
            hfoslog("Tile exists in cache", emitter="MTS", lvl=verbose)
            # Don't set cookies for static content
            response.cookie.clear()
            try:
                yield serve_file(request, response, filename)
            finally:
                event.stop()
        else:
            # We will have to get it first.
            hfoslog("Tile not cached yet. Tile data: ", filename, url,
                    emitter="MTS", lvl=verbose)
            if url in self._tilelist:
                hfoslog("Getting a tile for the second time?!", lvl=error,
                        emitter="MTS")
            else:
                self._tilelist += url
            try:
                tile, log = yield self.call(task(get_tile, url), "tcworkers")
                if log:
                    hfoslog("Thread error: ", log, emitter="MTS", lvl=error)
            except Exception as e:
                hfoslog("[MTS]", e, type(e))
                tile = None

            tilepath = os.path.dirname(filename)

            if tile:
                try:
                    os.makedirs(tilepath)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        hfoslog("Couldn't create path: %s (%s)" % (e, type(e)),
                                exc=True, emitter="MTS")

                hfoslog("Caching tile.", lvl=verbose, emitter="MTS")
                try:
                    with open(filename, "wb") as tilefile:
                        try:
                            tilefile.write(bytes(tile))
                        except Exception as e:
                            hfoslog("Writing error: %s" % str([type(e), e]),
                                    emitter="MTS")

                except Exception as e:
                    hfoslog("Open error: %s" % str([type(e), e]),
                            emitter="MTS")
                    return
                finally:
                    event.stop()

                try:
                    hfoslog("Delivering tile.", lvl=verbose, emitter="MTS")
                    yield serve_file(request, response, filename)
                except Exception as e:
                    hfoslog("Couldn't deliver tile: ", e, lvl=error,
                            emitter="MTS")
                    event.stop()
                hfoslog("Tile stored and delivered.", lvl=verbose,
                        emitter="MTS")
            else:
                hfoslog("Got no tile, serving defaulttile: %s" % url,
                        emitter="MTS")
                if self.defaulttile:
                    try:
                        yield serve_file(request, response, self.defaulttile)
                    finally:
                        event.stop()
                else:
                    yield
