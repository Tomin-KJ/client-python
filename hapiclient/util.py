def setopts(defaults, given):
    """Override default keyword dictionary options.

        kwargs = setopts(defaults, kwargs)

        A warning is shown if kwargs contains a key not found in default.
    """
    from inspect import stack
    fname = stack()[1][1]

    # Override defaults
    for key, value in given.items():
        if key in defaults:
            defaults[key] = value
        else:
            warning('Ignoring invalid keyword option "%s".' % key, fname)

    return defaults

def log(msg, opts):
    """Print message to console."""

    import sys

    if opts['logging']:
        if pythonshell() == 'jupyter-notebook':
            # Don't show full path information.
            msg = msg.replace(opts['cachedir'] + '/', '')
            msg = msg.replace(opts['cachedir'], '')
        pre = sys._getframe(1).f_code.co_name + '(): '
        print(pre + msg)

def jsonparse(res):
    """Try/catch of json.load() function with short error message."""

    from json import load
    try:
        return load(res)
    except:
        error('Could not parse JSON from %s' % res.geturl())

def printf(format, *args):
    """Emulation of more common printf() print function."""

    from sys import stdout
    stdout.write(format % args)

def system(cmd):
    """Execute system command and return exit code, stderr, and stdout.

        exitcode, stderr, stdout = system(cmd)

        If execution fails, an OSError is raised.
    """

    #TODO: Document difference between exitcode != 0 and OSError

    from shlex import split
    from subprocess import Popen, PIPE
    try:
        args = split(cmd)
        proc = Popen(args, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        exitcode = proc.returncode
        return exitcode, out.decode(), err.decode()
    except OSError as err:
        msg = "Execution failed: " + cmd + "\n" + err[1]
        raise OSError(msg)

def pythonshell():
    """Determine python shell

    pythonshell() returns

    'shell' (started python on command line using "python")
    'ipython' (started ipython on command line using "ipython")
    'ipython-notebook' (running in Spyder or started with "ipython qtconsole")
    'jupyter-notebook' (running in a Jupyter notebook)

    See also https://stackoverflow.com/a/37661854
    """

    from os import environ, path
    env = environ
    shell = 'shell'
    program = path.basename(env['_'])

    if 'jupyter-notebook' in program:
        shell = 'jupyter-notebook'
    elif 'JPY_PARENT_PID' in env or 'ipython' in program:
        shell = 'ipython'
        if 'JPY_PARENT_PID' in env:
            shell = 'ipython-notebook'

    return shell

def warning_test():
    """For testing warning function."""

    # Should show warnings in order and only HAPIWarning {1,2} should
    # have a different format
    from warnings import warn
    from hapiclient.util import warning

    warn('Normal warning 1')
    warn('Normal warning 2')

    warning('HAPI Warning 1')
    warning('HAPI Warning 2')

    warn('Normal warning 3')
    warn('Normal warning 4')

def warning(*args):
    """Display a short warning message.

    warning(message) raises a warning of type HAPIWarning and displays
    "Warning: " + message. Use for warnings when a full stack trace is not
    needed.
    """

    import warnings
    from os import path
    from sys import stderr
    from inspect import stack

    message = args[0]
    if len(args) > 1:
        fname = args[1]
    else:
        fname = stack()[1][1]

    #line = stack()[1][2]

    fname = path.basename(fname)

    # Custom warning format function
    def _warning(message, category=UserWarning, filename='', lineno=-1, file=None, line=''):
        if category.__name__ == "HAPIWarning":
            stderr.write("\x1b[31mWarning in " + fname + "\x1b[0m: " + str(message) + "\n")
        else:
            # Use default showwarning function.
            showwarning_default(message, category=UserWarning,
                                filename='', lineno=-1,
                                file=None, line='')

        stderr.flush()

        # Reset showwarning function to default
        warnings.showwarning = showwarning_default

    class HAPIWarning(Warning):
        pass

    # Copy default showwarning function
    showwarning_default = warnings.showwarning

    # Use custom warning function instead of default
    warnings.showwarning = _warning

    # Raise warning
    warnings.warn(message, HAPIWarning)

def error(msg):
    """Display a short error message.

    error(message) raises an error of type HAPIError and displays
    "Error: " + message. Use for errors when a full stack trace is not needed.
    """

    # TODO: Pass debug as a keyword or set in __init__.py?
    debug = False # If True, full stack trace is shown.

    import sys
    from inspect import stack
    from os import path

    from IPython.core.interactiveshell import InteractiveShell

    fname = stack()[1][1]
    fname = path.basename(fname)
    #line = stack()[1][2]

    def exception_handler_ipython(self, exc_tuple=None,
                                  filename=None, tb_offset=None,
                                  exception_only=False,
                                  running_compiled_code=False):

        #import traceback
        exception = sys.exc_info()
        if not debug and exception[0].__name__ == "HAPIError":
            sys.stderr.write("\x1b[31mError: \x1b[0m" + str(exception[1]))
        else:
            # Use default
            showtraceback_default(self, exc_tuple=None,
                                  filename=None, tb_offset=None,
                                  exception_only=False,
                                  running_compiled_code=False)

        sys.stderr.flush()

        # Reset back to default
        InteractiveShell.showtraceback = showtraceback_default

    def exception_handler(exception_type, exception, traceback):

        if not debug and exception[0].__name__ == "HAPIError":
            print("%s: %s" % (exception_type.__name__, exception))
        else:
            # Use default.
            sys.__excepthook__(exception_type, exception, traceback)

        sys.stderr.flush()

        # Reset back to default
        sys.excepthook = sys.__excepthook__

    class HAPIError(Exception): pass

    try:
        # Copy default function
        showtraceback_default = InteractiveShell.showtraceback
        # TODO: Use set_custom_exc
        # https://ipython.readthedocs.io/en/stable/api/generated/IPython.core.interactiveshell.html
        InteractiveShell.showtraceback = exception_handler_ipython
    except:
        # IPython over-rides this, so this does nothing in IPython shell.
        # https://stackoverflow.com/questions/1261668/cannot-override-sys-excepthook
        # Don't need to copy default function as it is provided as sys.__excepthook__.
        sys.excepthook = exception_handler

    raise HAPIError(msg)

##############################################################################
# Start compatability code
def input(msg):
    import sys
    if sys.version_info[0] > 2:
        input(msg)
    else:
        raw_input(msg)

def download(file, url, **kwargs):
    """Download a file if local version is older than server version."""

    #TODO: Make Python 2 compatable.

    from os import stat, utime, path, makedirs
    from time import mktime, strptime

    opts = kwargs
    debug = False

    dir = path.dirname(file)
    if not path.exists(dir):
        makedirs(dir)

    # If download is needed
    download = False

    # HEAD request on url
    log('Making head request on ' + url, opts)
    headers = head(url)
    # TODO: Write headers to file.head
    if debug: print("Header:\n--\n")
    if debug: print(headers)
    if debug: print("--")

    if path.exists(file):
        # TODO: Get this from file.head
        fileLastModified = stat(file).st_mtime
        if "Last-Modified" in headers:
            urlLastModified = mktime(strptime(headers["Last-Modified"],
                                              "%a, %d %b %Y %H:%M:%S GMT"))
            if urlLastModified > fileLastModified:
                download = True
            if debug: print("File Last Modified = %s" % fileLastModified)
            if debug: print("URL Last Modified = %s" % urlLastModified)
        else:
            if debug: print("No Last-Modified header. Will re-download")
            # TODO: Read file.head and compare etag
            download = True
    else:
        download = True

    if download:
        log('Downloading ' + url + ' to ' + file, opts)
        # TODO: try/catch
        req = urlretrieve(url, file)
        headers = req[1]
        if "Last-Modified" in headers:
            # Change access and modfied time to match that on server.
            # TODO: Won't need if using file.head.
            urlLastModified = mktime(strptime(headers["Last-Modified"],
                                              "%a, %d %b %Y %H:%M:%S GMT"))
            utime(file, (urlLastModified, urlLastModified))
    else:
        log('Local version of ' + file + ' is up-to-date; using it.', kwargs)

def urlerror(e, url):
    """Handle a download error.

    urlerror(e, url) determines if e is a HAPI or URL library error, extracts
    the error message, and calls error().
    """

    from json import load

    def nonhapierror(e):

        body = ""
        try:
            body = e.read().decode('utf8')
        except:
            pass

        reason = ""
        if hasattr(e, 'reason'):
            reason = e.reason
        code = ""
        if hasattr(e, 'code'):
            code = e.code

        if len(body) > 0:
            error('"HTTP %d - %s" returned by %s. Response body:\n%s' % (code, reason, url, body))
        elif code != "":
            error('"HTTP %d - %s" returned by %s.' % (code, reason, url))
        else:
            error('Error message: "%s" when trying to read %s.' % (reason, url))

    try:
        jres = load(e)
        if 'status' in jres:
            if 'message' in jres['status']:
                error('\n%s\n  %s\n' % (url, jres['status']['message']))
                return
        nonhapierror(e)
    except:
        nonhapierror(e)

def head(url):

    import sys

    if sys.version_info[0] > 2:
        import urllib.request, urllib.error
        try:
            headers = urllib.request.urlopen(url).info()
        except urllib.error.URLError as e:
            urlerror(e, url)
        except ValueError:
            error("'" + url + "' is not a valid URL")
    else:
        import urllib
        import urllib2
        try:
            headers = urllib2.urlopen(url).info()
        except urllib2.URLError as e:
            urlerror(e, url)
        except ValueError:
            error("'" + url + "' is not a valid URL")

    return headers

def urlquote(url):
    import sys
    if sys.version_info[0] > 2:
        import urllib.parse
        return urllib.parse.quote(url)
    else:
        from urllib import quote
        return quote(url)
        
    
def urlopen(url):
    """Python 2/3 urllib urlopen compatability function.

    If Python 3, calls
    urllib.request.urlopen(url, fname)

    If Python 2, calls
    urllib.urlopen(url, fname) (Python 2)
    """

    import sys

    if sys.version_info[0] > 2:
        import urllib.request, urllib.error
        try:
            res = urllib.request.urlopen(url)
        except urllib.error.URLError as e:
            urlerror(e, url)
        except ValueError:
            error("'" + url + "' is not a valid URL")
    else:
        import urllib
        import urllib2
        try:
            res = urllib2.urlopen(url)
        except urllib2.URLError as e:
            urlerror(e, url)
        except ValueError:
            error("'" + url + "' is not a valid URL")

    return res

def urlretrieve(url, fname):
    """Python 2/3 urllib urlretrieve compatability function.

    If Python 3, calls
    urllib.request.urlretrieve(url, fname)

    If Python 2, calls
    urllib.urlretrieve(url, fname) (Python 2)
    """

    import sys

    if sys.version_info[0] > 2:
        import urllib.request, urllib.error
        try:
            res = urllib.request.urlretrieve(url, fname)
            return res
        except urllib.error.URLError as e:
            urlerror(e, url)
        except ValueError as e:
            error("'" + url + "' is not a valid URL")
    else:
        import urllib
        import urllib2
        try:
            res = urllib.urlretrieve(url, fname)
            return res
        except urllib2.URLError as e:
            urlerror(e, url)
        except ValueError:
            error("'" + url + "' is not a valid URL")
# End compatability code
##############################################################################
