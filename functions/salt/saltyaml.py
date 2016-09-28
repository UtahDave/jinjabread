# -*- coding: utf-8 -*-
'''
YAML Renderer for Salt
For YAML usage information see :ref:`Understanding YAML <yaml>`.
'''

from __future__ import absolute_import

# Import python libs
import logging
import warnings
from yaml.scanner import ScannerError
from yaml.parser import ParserError
from yaml.constructor import ConstructorError

# Import salt libs
#import salt.utils.url
from yaml import load
from .yamlloader import SaltYamlSafeLoader
from .odict import OrderedDict
from .saltexceptions import SaltRenderError
import six as six
from .six import string_types
from .six.moves import range

log = logging.getLogger(__name__)

_ERROR_MAP = {
    ("found character '\\t' that cannot "
     "start any token"): 'Illegal tab character'
}


def get_yaml_loader(argline):
    '''
    Return the ordered dict yaml loader
    '''
    def yaml_loader(*args):
        return SaltYamlSafeLoader(*args, dictclass=OrderedDict)
    return yaml_loader


def render(yaml_data, saltenv='base', sls='', argline='', **kws):
    '''
    Accepts YAML as a string or as a file object and runs it through the YAML
    parser.
    :rtype: A Python data structure
    '''
    if not isinstance(yaml_data, string_types):
        yaml_data = yaml_data.read()
    with warnings.catch_warnings(record=True) as warn_list:
        try:
            data = load(yaml_data, Loader=get_yaml_loader(argline))
        except ScannerError as exc:
            err_type = _ERROR_MAP.get(exc.problem, exc.problem)
            line_num = exc.problem_mark.line  #+ 1
            raise SaltRenderError(err_type, line_num, exc.problem_mark.buffer)
            #return SaltRenderError(err_type, line_num, exc.problem_mark.buffer)
        except (ParserError, ConstructorError) as exc:
            raise SaltRenderError(exc)
            #return SaltRenderError(exc)
        if len(warn_list) > 0:
            for item in warn_list:
                log.warning(
                    '{warn} found in {sls} saltenv={env}'.format(
                        warn=item.message, sls=salt.utils.url.create(sls), env=saltenv
                    )
                )
        if not data:
            data = {}
        else:
            data = _yaml_result_unicode_to_utf8(data)
        #log.debug('Results of YAML rendering: \n{0}'.format(data))

        def _validate_data(data):
            '''
            PyYAML will for some reason allow improper YAML to be formed into
            an unhashable dict (that is, one with a dict as a key). This
            function will recursively go through and check the keys to make
            sure they're not dicts.
            '''
            if isinstance(data, dict):
                for key, value in six.iteritems(data):
                    if isinstance(key, dict):
                        raise SaltRenderError(
                            'Invalid YAML, possible double curly-brace')
                    _validate_data(value)
            elif isinstance(data, list):
                for item in data:
                    _validate_data(item)

        _validate_data(data)
        return data


def _yaml_result_unicode_to_utf8(data):
    ''''
    Replace `unicode` strings by utf-8 `str` in final yaml result
    This is a recursive function
    '''
    if six.PY3:
        return data
    if isinstance(data, OrderedDict):
        for key, elt in six.iteritems(data):
            data[key] = _yaml_result_unicode_to_utf8(elt)
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = _yaml_result_unicode_to_utf8(data[i])
    elif isinstance(data, six.text_type):
        # here also
        data = data.encode('utf-8')
    return data
