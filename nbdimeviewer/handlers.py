# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function
from __future__ import unicode_literals

import requests
import json

from six import string_types

import nbformat

from tornado import web, escape

from nbdime.webapp.nbdimeserver import ApiDiffHandler, MainDiffHandler


class NbdimeViewerApiHandler(ApiDiffHandler):
    def get_notebook_argument(self, argname):
        """Override default to prevent reading of local files
        """
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
            raise web.HTTPError(400, "Invalid notebook: %s" % arg)

        return nb
