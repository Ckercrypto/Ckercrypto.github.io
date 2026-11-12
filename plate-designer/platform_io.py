"""Platform specific file locations, publishing exports, sharing and picking files.

Android code paths use androidstorage4kivy (MediaStore / Storage Access
Framework) and are only imported on Android."""
import os
import subprocess
import sys

try:
    from kivy.utils import platform
except Exception:  # pragma: no cover
    platform = sys.platform

IS_ANDROID = platform == 'android'
IS_WINDOWS = platform == 'win'

MIME = {'.pdf': 'application/pdf', '.png': 'image/png', '.svg': 'image/svg+xml',
        '.tplate': 'application/json'}


def documents_dir():
    """Desktop: ~/Documents/TransPlate (created on demand)."""
    home = os.path.expanduser('~')
    docs = os.path.join(home, 'Documents')
    if IS_WINDOWS:
        try:
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)  # CSIDL_PERSONAL
            if buf.value:
                docs = buf.value
        except Exception:
            pass
    if not os.path.isdir(docs):
        docs = home
    d = os.path.join(docs, 'TransPlate')
    os.makedirs(d, exist_ok=True)
    return d


def app_dirs(user_data_dir):
    if IS_ANDROID:
        base = user_data_dir
        projects = os.path.join(base, 'projects')
        exports = os.path.join(base, 'exports')
    else:
        base = documents_dir()
        projects = os.path.join(base, 'projects')
        exports = base
    for d in (projects, exports):
        os.makedirs(d, exist_ok=True)
    return {'projects': projects, 'exports': exports, 'data': user_data_dir}


def request_android_permissions():
    if not IS_ANDROID:
        return
    try:
        from android import api_version
        from android.permissions import Permission, request_permissions
        if api_version < 29:
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                                 Permission.READ_EXTERNAL_STORAGE])
    except Exception as e:  # pragma: no cover
        print('permission request failed', e)


def publish(path):
    """Make an exported file visible to the user.

    Android: copy into shared storage (Documents/ or Pictures/ via MediaStore)
    and return (uri, human description).  Desktop: the file already lives in
    Documents/TransPlate, return (path, path)."""
    if IS_ANDROID:
        try:
            from androidstorage4kivy import SharedStorage
            ext = os.path.splitext(path)[1].lower()
            coll = None
            try:
                from jnius import autoclass
                Environment = autoclass('android.os.Environment')
                coll = (Environment.DIRECTORY_PICTURES if ext == '.png'
                        else Environment.DIRECTORY_DOCUMENTS)
            except Exception:
                coll = None
            # default sub-folder inside the collection is the app's name
            uri = SharedStorage().copy_to_shared(path, collection=coll)
            where = ('Pictures' if ext == '.png' else 'Documents') + ' / ' + \
                os.path.basename(path)
            return uri, where
        except Exception as e:
            print('SharedStorage failed:', e)
            return None, path
    return path, path


def share(uri_or_path):
    if IS_ANDROID:
        try:
            from androidstorage4kivy import ShareSheet
            ShareSheet().share_file(uri_or_path)
            return True
        except Exception as e:
            print('share failed', e)
            return False
    return open_folder(os.path.dirname(uri_or_path)) if uri_or_path else False


def open_folder(path):
    try:
        if IS_WINDOWS:
            os.startfile(path)  # noqa
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        elif not IS_ANDROID:
            subprocess.Popen(['xdg-open', path])
        return True
    except Exception as e:
        print('open folder failed', e)
        return False


def android_pick_file(mime, callback):
    """Android: system file picker; callback(private_path) on the Kivy thread."""
    from androidstorage4kivy import Chooser, SharedStorage
    from kivy.clock import Clock

    def chosen(uris):
        try:
            if uris:
                p = SharedStorage().copy_from_shared(uris[0])
                Clock.schedule_once(lambda dt: callback(p), 0)
        except Exception as e:
            print('pick failed', e)

    # keep a reference so the activity result listener survives
    android_pick_file._chooser = Chooser(chosen)
    android_pick_file._chooser.choose_content(mime)
