# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function
from __future__ import unicode_literals

import io
import os
import sys
from argparse import ArgumentParser

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from tornado import ioloop, web, netutil, httpserver, log
from tornado.httpclient import AsyncHTTPClient
import tornado.options
from tornado.options import define, options

from nbdime.args import add_generic_args, add_web_args
from nbdime.webapp.nbdimeserver import MainDiffHandler
import nbdime

try:
    from .client import NBViewerCurlAsyncHTTPClient as HTTPClientClass
except ImportError:
    from .client import NBViewerSimpleAsyncHTTPClient as HTTPClientClass

from .cache import DummyAsyncCache, AsyncMultipartMemcache, MockCache, pylibmc
from .index import NoSearch, ElasticSearch
from .handlers import NbdimeViewerApiHandler
from .log import log_request
from .utils import url_path_join


nbdime_webapp_path = os.path.abspath(os.path.dirname(nbdime.webapp.nbdimeserver.__file__))
static_path = os.path.join(nbdime_webapp_path, "static")
template_path = os.path.join(nbdime_webapp_path, "templates")



def make_app(**params):
    handlers = [
        (r"/", MainDiffHandler, params),
        (r"/api/diff", NbdimeViewerApiHandler, params),
        (r"/static", web.StaticFileHandler, {"path": static_path}),
    ]

    # DEBUG env implies both autoreload and log-level
    if os.environ.get("DEBUG"):
        options.debug = True
        logging.getLogger().setLevel(logging.DEBUG)



    # setup memcache
    mc_pool = ThreadPoolExecutor(options.mc_threads)

    if options.processes:
        pool = ProcessPoolExecutor(options.processes)
    else:
        pool = ThreadPoolExecutor(options.threads)

    memcache_urls = os.environ.get('MEMCACHIER_SERVERS',
        os.environ.get('MEMCACHE_SERVERS')
    )

    # Handle linked Docker containers
    if(os.environ.get('NBCACHE_PORT')):
        tcp_memcache = os.environ.get('NBCACHE_PORT')
        memcache_urls = tcp_memcache.split('tcp://')[1]

    if(os.environ.get('NBINDEX_PORT')):
        log.app_log.info("Indexing notebooks")
        tcp_index = os.environ.get('NBINDEX_PORT')
        index_url = tcp_index.split('tcp://')[1]
        index_host, index_port = index_url.split(":")
        indexer = ElasticSearch(index_host, index_port)
    else:
        log.app_log.info("Not indexing notebooks")
        indexer = NoSearch()

    if options.no_cache:
        log.app_log.info("Not using cache")
        cache = MockCache()
    elif pylibmc and memcache_urls:
        kwargs = dict(pool=mc_pool)
        username = os.environ.get('MEMCACHIER_USERNAME', '')
        password = os.environ.get('MEMCACHIER_PASSWORD', '')
        if username and password:
            kwargs['binary'] = True
            kwargs['username'] = username
            kwargs['password'] = password
            log.app_log.info("Using SASL memcache")
        else:
            log.app_log.info("Using plain memecache")

        cache = AsyncMultipartMemcache(memcache_urls.split(','), **kwargs)
    else:
        log.app_log.info("Using in-memory cache")
        cache = DummyAsyncCache()

    AsyncHTTPClient.configure(HTTPClientClass)
    client = AsyncHTTPClient()
    client.cache = cache

    fetch_kwargs = dict(connect_timeout=10,)
    if options.proxy_host:
        fetch_kwargs.update(dict(proxy_host=options.proxy_host,
                                 proxy_port=options.proxy_port))

        log.app_log.info("Using web proxy {proxy_host}:{proxy_port}."
                         "".format(**fetch_kwargs))

    if options.no_check_certificate:
        fetch_kwargs.update(dict(validate_cert=False))

        log.app_log.info("Not validating SSL certificates")


    settings = dict(
        static_path=static_path,
        template_path=template_path,
        log_function=log_request,
        static_url_prefix=url_path_join(options.base_url, '/static/'),
        client=client,
        index=indexer,
        cache=cache,
        cache_expiry_min=options.cache_expiry_min,
        cache_expiry_max=options.cache_expiry_max,
        pool=pool,
        gzip=True,
        render_timeout=options.render_timeout,
        fetch_kwargs=fetch_kwargs,
        base_url=options.base_url
    )

    return web.Application(handlers, debug=options.debug, **settings)


def init_options():
    # command-line options
    if 'port' in options:
        # already run
        return

    define("debug", default=False, help="run in debug mode", type=bool)
    define("no_cache", default=False, help="Do not cache results", type=bool)
    define("port", default=5001, help="run on the given port", type=int)
    define("address", default="0.0.0.0", help="listen on the given address", type=str)
    define("cache_expiry_min", default=10*60, help="minimum cache expiry (seconds)", type=int)
    define("cache_expiry_max", default=2*60*60, help="maximum cache expiry (seconds)", type=int)
    define("render_timeout", default=15, help="Time to wait for a render to complete before showing the 'Working...' page.", type=int)
    define("mc_threads", default=1, help="number of threads to use for Async Memcache", type=int)
    define("threads", default=1, help="number of threads to use for rendering", type=int)
    define("processes", default=0, help="use processes instead of threads for rendering", type=int)
    define("sslcert", help="path to ssl .crt file", type=str)
    define("sslkey", help="path to ssl .key file", type=str)
    define("no_check_certificate", default=False, help="Do not validate SSL certificates", type=bool)
    define("default_format", default="html", help="format to use for legacy / URLs", type=str)
    define("proxy_host", default="", help="The proxy URL.", type=str)
    define("proxy_port", default="", help="The proxy port.", type=int)
    define("base_url", default="/", help="URL base for the server")

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    init_options()
    tornado.options.parse_command_line(argv)

     # create and start the app
    app = make_app()

    # load ssl options
    ssl_options = None
    if options.sslcert:
        ssl_options = {
            'certfile' : options.sslcert,
            'keyfile' : options.sslkey,
        }

    http_server = httpserver.HTTPServer(app, xheaders=True, ssl_options=ssl_options)
    log.app_log.info("Listening on port %i", options.port)
    port = options.port
    if port != 0 or on_port is None:
        http_server.listen(options.port)
    else:
        sockets = netutil.bind_sockets(0, address)
        http_server.add_sockets(sockets)
        for s in sockets:
            print('Listening on %s, port %d' % s.getsockname()[:2])
            port = s.getsockname()[1]
    ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
