"""Exercise the Android-only code paths of platform_io with fake modules
(androidstorage4kivy / android / jnius are not available off-device).
This checks our call sequence, not the real Android APIs."""
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

calls = []


class FakeShared:
    def copy_to_shared(self, path, collection=None, filepath=None):
        calls.append(('copy_to_shared', os.path.basename(path), collection))
        return 'content://media/external/file/42'

    def copy_from_shared(self, uri):
        calls.append(('copy_from_shared', uri))
        return '/data/user/0/org.transreza.platedesigner/cache/picked.png'


class FakeShare:
    def share_file(self, uri, app=None):
        calls.append(('share_file', uri))


class FakeChooser:
    def __init__(self, cb):
        self.cb = cb

    def choose_content(self, mime):
        calls.append(('choose_content', mime))
        self.cb(['content://picked'])


a4k = types.ModuleType('androidstorage4kivy')
a4k.SharedStorage, a4k.ShareSheet, a4k.Chooser = FakeShared, FakeShare, FakeChooser
sys.modules['androidstorage4kivy'] = a4k
jn = types.ModuleType('jnius')


class _Env:
    DIRECTORY_DOCUMENTS = 'Documents'
    DIRECTORY_PICTURES = 'Pictures'


jn.autoclass = lambda name: _Env
sys.modules['jnius'] = jn
andr = types.ModuleType('android')
andr.api_version = 28
perm = types.ModuleType('android.permissions')


class Permission:
    WRITE_EXTERNAL_STORAGE = 'W'
    READ_EXTERNAL_STORAGE = 'R'


perm.Permission = Permission
perm.request_permissions = lambda p: calls.append(('request_permissions', tuple(p)))
sys.modules['android'] = andr
sys.modules['android.permissions'] = perm

import platform_io  # noqa: E402

platform_io.IS_ANDROID = True


def test_android_paths():
    import tempfile
    d = platform_io.app_dirs(tempfile.mkdtemp())
    assert d['projects'].endswith('projects') and d['exports'].endswith('exports')
    uri, where = platform_io.publish('/x/plate.pdf')
    assert uri.startswith('content://') and where.startswith('Documents')
    uri2, where2 = platform_io.publish('/x/plate.png')
    assert where2.startswith('Pictures')
    assert platform_io.share(uri)
    platform_io.request_android_permissions()
    got = []
    from kivy.clock import Clock
    platform_io.android_pick_file('image/*', got.append)
    Clock.tick()
    Clock.tick()
    assert ('copy_to_shared', 'plate.pdf', 'Documents') in calls
    assert ('copy_to_shared', 'plate.png', 'Pictures') in calls
    assert ('share_file', 'content://media/external/file/42') in calls
    assert ('request_permissions', ('W', 'R')) in calls
    assert ('choose_content', 'image/*') in calls
    assert got == ['/data/user/0/org.transreza.platedesigner/cache/picked.png'], got


if __name__ == '__main__':
    test_android_paths()
    print('ok android mock', calls)
