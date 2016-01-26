""" Generic configuration.

A Config object has a set of options, which can be str, int, float,
bool, or list. These options can be configured from different sources:

* Each option has a default value
* From a set of common ``.cfg`` files, and additional filenames given
    during initialization.
* From environment variables.
* From command-line arguments.
* By setting the config option directly.

For example, an option 'foo' in a config named 'myconfig' can
be set:

* With an entry ``foo = 3`` in '<appdata>/.myconfig.cfg' in the section
    'myconfig'.
* With an environment variable named ``MYCONFIG_FOO``. 
* With a command line argument ``--myconfig-foo``.
* By doing ``c.foo = 3``, or `c['foo'] = 3 in Python.

In all cases except setting the property directly, the option name
is case insensitive.

An example to create a config class:

    class MyConfig(Config):
        
        @Config.prop
        def foo(value):
            ''' An example integer option. '''
            return Config.as_int(value)
        
        @Config.prop
        def bar(value):
            ''' An example option that is a list of floats. '''
            return [Config.as_float(x) for x in Config.as_list(value)]
"""

from __future__ import print_function, absolute_import

import os
import sys
import logging


BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                  '0': False, 'no': False, 'false': False, 'off': False}

def as_bool(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, str) and value.lower() in BOOLEAN_STATES:
        return BOOLEAN_STATES[value.lower()]
    else:
        raise ValueError('Cannot make a bool of %r' % value)

if sys.version_info[0] == 2:
    import ConfigParser as configparser
    TYPEMAP = {basestring:unicode, float:float, int:int, bool:as_bool}
else:
    import configparser
    TYPEMAP = {str:str, float:float, int:int, bool:as_bool}

def is_valid_name(n):
    return isinstance(n, str) and n.isidentifier() and not n.startswith('_')


INSTANCE_DOCS = """ Configuration object for {name}
    
    The options below can be set via a ``.cfg`` file, environment variable,
    command-line argument, or directly in Python.
    
    Parameters:
    """


class Config:
    """ Class for configuration objects.
    
    Parameters:
        name (str): the name by which to identify this config. This name
            is used in prefixes in environment variables and command
            line arguments, and as a section header in .cfg files.
        *sources: Additional sources to initialize the option values with.
            These can be strings in .cfg format, or filenames of .cfg files.
        **options: The options specification: each option consists of
            a 3-element tuple (default, type, docstring).
    
    The options can be of the following types, str, bool, int, float.
    Values (also default values) can be specified as a Python object
    or a string; they are automatically converted to a Python object.
    
    Example:
    
        config = Config('myconfig', 
                        foo=(False, bool, 'Whether to foo'),
                        bar=(0.0, float, 'The size of the bar'))
        
        config.bar = 3  # Attribute access (values are converted)
        print(config['FOO'])  # Case insensitive
        print(config.__doc__)  # A fancy docstring for Sphynx!
    
    Note: this docstring is modified for each instance of this class.
    """
    
    def __init__(self, name, *sources, **options):
        
        # The identifier name for this config
        self._name = name
        if not is_valid_name(name):
            raise ValueError('Config name must be an alphanumeric string, '
                             'starting with a letter.')
        
        # The option names (unmodified case)
        self._options = []
        
        # Where the values are stored, we keep a "history", lowercase keys
        self._opt_values = {}  # name -> list of (source, value) tuples
        
        # Map of option names to validator functions, lowercase keys
        self._opt_validators = {}
        
        # Parse options
        if not isinstance(options, dict):
            raise TypeError('Config needs dict argument for the options.')
        option_docs = ['']
        for name, spec in options.items():
            # Checks
            if not is_valid_name(name):
                raise ValueError('Option name must be alphanumeric strings, '
                                 'starting with a letter, and not private.')
            if not len(spec) == 3:
                raise ValueError('Option spec must be (default, type, docs)')
            default, typ, doc = spec
            if not (isinstance(typ, type) and issubclass(typ, tuple(TYPEMAP))):
                raise ValueError('Option types can be str, bool, int, float.')
            # Parse
            args = name, typ, doc, default
            option_docs.append(' '*8 + '%s (%s): %s (default %r)' % args)
            self._options.append(name)
            self._opt_validators[name.lower()] = TYPEMAP[typ]
            self._opt_values[name.lower()] = []
        
        # Overwrite docstring
        self.__doc__ = INSTANCE_DOCS.format(name=self._name)
        self.__doc__ += '\n'.join(option_docs)
        
        # --- init values
        
        # Set defaults
        for name, spec in options.items():
            self._set('default', name, spec[0])
        
        # Load from sources
        filenames = [appdata_dir(self._name) + '.cfg',
                     os.path.join(appdata_dir(self._name), 'config.cfg'),
                     os.path.join(application_dir() or '', 'config.cfg')]
        for source in filenames + list(sources):
            if not isinstance(source, str):
                raise ValueError('Sources should be strings or filenames.')
            text = ''
            if '\n' in source:
                text, filename = source, '<string>'
            elif os.path.isfile(source):
                filename = source
                try:
                    text = open(source, 'rb').read().decode()
                except Exception as err:
                    logging.warn('Could not read config from %r:\n%s' %
                                 (filename, str(e)))
            if text:
                try:
                    self._load_from_string(text, filename)
                except Exception as err:
                    logging.warn('Could not parse config from %r:\n%s' %
                                (filename, str(e)))
        
        # Load from environ
        for name in self._opt_values:
            env_name = (self._name + '_' + name).upper()
            value = os.getenv(env_name, None)  # getenv is case insensitive
            if value is not None:
                self._set('environ', name, value)
        
        # # Load from string
        # if isinstance(string, str):
        #     self._load_from_string(string)
        # elif string is not None:
        #     raise ValueError('String should be a str object.')
        
        # Load from argv
        arg_prefix = '--' + self._name + '-'
        for i in range(1, len(sys.argv)-1):
            arg = sys.argv[i]
            if arg.startswith(arg_prefix):
                name = arg[len(arg_prefix):]
                if name.lower() in self._opt_values:
                    self._set('argv', name, sys.argv[i+1])
    
    def __repr__(self):
        t = '<Config %r with %i options at 0x%x>'
        return t % (self._name, len(self._options), id(self))
    
    def __iter__(self):
        return self._options.__iter__()
    
    def __dir__(self):
        return self._options
    
    def __getattr__(self, name):
        # Case sensitive get
        if not name.startswith('_') and name in self._options:
            return self._opt_values[name.lower()][-1][1]
        return super().__getattribute__(name)
    
    def __getitem__(self, name):
        # Case insensitive get
        if not isinstance(name, str):
            raise TypeError('Config only allows subscripting by name strings.')
        if name.lower() in self._opt_values:
            return self._opt_values[name.lower()][-1][1]
        else:
            raise IndexError('Config has no option %r' % name)
    
    def __setattr__(self, name, value):
        # Case sensitive set
        if not name.startswith('_') and name in self._options:
            return self._set('set', name, value)
        return super().__setattr__(name, value)
    
    def __setitem__(self, name, value):
        # Case insensitve set
        if not isinstance(name, str):
            raise TypeError('Config only allows subscripting by name strings.')
        if name.lower() in self._opt_values:
            return self._set('set', name, value)
        else:
            raise IndexError('Config has no option %r' % name)
    
    def _set(self, source, name, value):
        # The actual setter (case insensitive), applies the validator
        validator = self._opt_validators[name.lower()]
        real_value = validator(value)
        s = self._opt_values[name.lower()]
        if s and s[-1][0] == source:
            s[-1] = source, real_value
        else:
            s.append((source, real_value))
    
    def _load_from_string(self, s, filename='<string>'):
        parser = configparser.ConfigParser()
        parser.read_string(s, filename)
        
        if parser.has_section(self._name):
            for name in self._options:
                if parser.has_option(self._name, name):
                    value = parser.get(self._name, name)
                    self._set(filename, name, value)


# From pyzolib/paths.py (https://bitbucket.org/pyzo/pyzolib/src/tip/paths.py)
def appdata_dir(appname=None, roaming=False):
    """ Get the path to the application directory, where applications
    are allowed to write user specific files (e.g. configurations).
    """
    # Define default user directory
    userDir = os.path.expanduser('~')
    # Get system app data dir
    path = None
    if sys.platform.startswith('win'):
        path1, path2 = os.getenv('LOCALAPPDATA'), os.getenv('APPDATA')
        path = (path2 or path1) if roaming else (path1 or path2)
    elif sys.platform.startswith('darwin'):
        path = os.path.join(userDir, 'Library', 'Application Support')
    # On Linux and as fallback
    if not (path and os.path.isdir(path)):
        path = userDir
    # Maybe we should store things local to the executable (in case of a
    # portable distro or a frozen application that wants to be portable)
    prefix = sys.prefix
    if getattr(sys, 'frozen', None):  # See application_dir() function
        prefix = os.path.abspath(os.path.dirname(sys.path[0]))
    for reldir in ('settings', '../settings'):
        localpath = os.path.abspath(os.path.join(prefix, reldir))
        if os.path.isdir(localpath):  # pragma: no cover
            try:
                open(os.path.join(localpath, 'test.write'), 'wb').close()
                os.remove(os.path.join(localpath, 'test.write'))
            except IOError:
                pass  # We cannot write in this directory
            else:
                path = localpath
                break
    # Get path specific for this app
    if appname:
        if path == userDir:
            appname = '.' + appname.lstrip('.')  # Make it a hidden directory
        path = os.path.join(path, appname)
        if not os.path.isdir(path):  # pragma: no cover
            os.mkdir(path)
    # Done
    return path


def application_dir():
    """ Get the directory in which the current application is located. 
    The "application" can be a Python script or a frozen application. 
    This function return None if in interpreter mode.
    """
    # Test if the current process can be considered an "application"
    if not sys.path or not sys.path[0]:
       return None
    # Get the path. If frozen, sys.path[0] is the name of the executable,
    # otherwise it is the path to the directory that contains the script.
    thepath = sys.path[0]
    if getattr(sys, 'frozen', None):
        thepath = os.path.dirname(thepath)
    # Return absolute version, or symlinks may not work
    return os.path.abspath(thepath)


if __name__ == '__main__':
   
   
    c = Config('test', 
               foo=(3, int, 'foo yeah'),
               spam=(2.1, float, 'a float!'))
    
