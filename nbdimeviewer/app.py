# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function
from __future__ import unicode_literals

import io
import os
import json
import sys
from argparse import ArgumentParser

import requests
from six import string_types
from tornado import ioloop, web, escape, netutil, httpserver
import nbformat

from nbdime.args import add_generic_args, add_web_args
from nbdime.webapp.nbdimeserver import ApiDiffHandler, MainDiffHandler

import nbdimeviewer
import nbdime


nbdime_webapp_path = os.path.abspath(os.path.dirname(nbdime.webapp.nbdimeserver.__file__))
static_path = os.path.join(nbdime_webapp_path, "static")
template_path = os.path.join(nbdime_webapp_path, "templates")


def truncate_filename(name):
    limit = 20
    if len(name) < limit:
        return name
    else:
        return name[:limit-3] + "..."


class NbdimeViewerApiHandler(ApiDiffHandler):
    def get_notebook_argument(self, argname):
        # Assuming a request on the form "{'argname':arg}"
        body = json.loads(escape.to_unicode(self.request.body))
        arg = body[argname]

        # Currently assuming arg is a URI
        if not isinstance(arg, string_types):
            raise web.HTTPError(400, "Expecting a URI.")

        r = requests.get(arg)

        # Let nbformat do the reading and validation
        try:
            nb = nbformat.reads(r.text, as_version=4)
        except:
            raise
            raise web.HTTPError(400, "Invalid notebook: %s" % truncate_filename(arg))

        return nb


def make_app(**params):
    handlers = [
        (r"/diff", MainDiffHandler, params),
        (r"/api/diff", NbdimeViewerApiHandler, params),
        (r"/static", web.StaticFileHandler, {"path": static_path}),
    ]

    settings = {
        "static_path": static_path,
        "template_path": template_path,
        }

    if nbdime.utils.is_in_repo(nbdimeviewer.__file__):
        # don't cache when working from repo
        settings.update({
            # "autoreload": True,
            "compiled_template_cache": False,
            "static_hash_cache": False,
            # "serve_traceback": True,
            })

    return web.Application(handlers, **settings)


def main_server(on_port=None, **params):
    print("Using params:")
    print(params)
    port = params.pop("port")
    app = make_app(**params)
    if port != 0 or on_port is None:
        app.listen(port, address='127.0.0.1')
    else:
        sockets = netutil.bind_sockets(0, '127.0.0.1')
        server = httpserver.HTTPServer(app)
        server.add_sockets(sockets)
        for s in sockets:
            print('Listening on %s, port %d' % s.getsockname()[:2])
            port = s.getsockname()[1]
    if on_port is not None:
        on_port(port)
    ioloop.IOLoop.current().start()
    return exit_code


def _build_arg_parser():
    """
    Creates an argument parser that lets the user specify a port
    and displays a help message.
    """
    description = 'Web interface for Nbdime.'
    parser = ArgumentParser(description=description)
    add_generic_args(parser)
    add_web_args(parser)
    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    arguments = _build_arg_parser().parse_args(args)
    return main_server(port=arguments.port, cwd=arguments.workdirectory)
