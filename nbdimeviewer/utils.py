
from contextlib import contextmanager


def url_path_join(*pieces):
    """Join components of url into a relative url
    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place
    """
    initial = pieces[0].startswith('/')
    final = pieces[-1].endswith('/')
    stripped = [s.strip('/') for s in pieces]
    result = '/'.join(s for s in stripped if s)
    if initial:
        result = '/' + result
    if final:
        result += '/'
    if result == '//':
        result = '/'
    return result


@contextmanager
def time_block(message):
    """context manager for timing a block
    logs millisecond timings of the block
    """
    tic = time.time()
    yield
    dt = time.time() - tic
    log = app_log.info if dt > 1 else app_log.debug
    log("%s in %.2f ms", message, 1e3 * dt)
