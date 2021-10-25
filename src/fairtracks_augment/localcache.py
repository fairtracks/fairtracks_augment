import os
import shutil
import yaml

from urllib.parse import urlparse
from yaml import YAMLObject

from fairtracks_augment.common import http_get_request, ArgBasedSingletonMeta
from fairtracks_augment.config import METADATA_FILE


class FileMetadata(YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = '!FileMetadata'

    def __init__(self, file_dir_path, filename, etag=None):
        self._file_dir_path = file_dir_path
        self._filename = filename
        self.etag = etag

    @classmethod
    def create_from_url(cls, file_dir_path, url):
        owl_file_name = os.path.basename(urlparse(url).path)
        return cls(file_dir_path, owl_file_name)

    def get_file_path(self):
        return os.path.join(self._file_dir_path, self._filename)


class LocalCache(metaclass=ArgBasedSingletonMeta):
    def __init__(self, filecache_dir_path, data_dir_path):
        self._filecache_dir_path = filecache_dir_path
        self._data_dir_path = data_dir_path
        self._metadata_file_path = os.path.join(self._data_dir_path, METADATA_FILE)
        self._file_metadata_dict = self._load_file_metadata()
        self._load_data_from_stored()

    def __del__(self):
        self.store()

    def store(self):
        self._store_file_metadata()
        self._store_data()

    def _load_file_metadata(self):
        if os.path.exists(self._metadata_file_path):
            with open(self._metadata_file_path, 'r') as yaml_file:
                return yaml.safe_load(yaml_file)
        return {}

    def _store_file_metadata(self):
        with open(self._metadata_file_path, 'w') as yaml_file:
            yaml.dump(self._file_metadata_dict, yaml_file)

    def all_file_urls(self):
        return list(self._file_metadata_dict.keys())

    def update_all_files(self):
        for url in self.all_file_urls():
            self.update_file(url)

    def install_or_update_file(self, url):
        if url not in self._file_metadata_dict:
            self.install_file(url)
        else:
            self.update_file(url)

    def install_file(self, url):
        self._assert_file_not_installed(url)

        self._register_file_metadata(url)

        print('downloading: ' + url)
        self._download_file(url)
        print('downloaded: ' + url)

        print('installing: ' + url)
        self._install_data_from_file(url)
        print('installed: ' + url)

        self._update_metadata_from_file(url)
        print('updated metadata: ' + url)

    def _assert_file_not_installed(self, url):
        assert url not in self._file_metadata_dict
        assert self._data_contains_url(url) in (None, False)

    def _assert_file_installed(self, url):
        assert url in self._file_metadata_dict
        assert self._data_contains_url(url) in (None, True)

    def _register_file_metadata(self, url):
        self._file_metadata_dict[url] = \
            self._get_metadata_cls().create_from_url(self._data_dir_path, url)

    def update_file(self, url):
        self._assert_file_installed(url)

        if self._does_file_need_update(url):
            self.delete_file(url)
            self.install_file(url)
            return True
        else:
            return False

    def _does_file_need_update(self, url):
        def _has_etag_changed_callback(response):
            return response.headers.get('etag') != self._file_metadata_dict[url].etag
        return http_get_request(self._filecache_dir_path, url,
                                callback_if_ok=_has_etag_changed_callback, require_etag=True)

    def _get_file_path(self, url):
        return self._file_metadata_dict[url].get_file_path()

    def _download_file(self, url):
        def _download_file_callback(response):
            self._file_metadata_dict[url].etag = response.headers['etag']
            with open(self._get_file_path(url), 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
        http_get_request(self._filecache_dir_path, url,
                         callback_if_ok=_download_file_callback, require_etag=True)

    def delete_file(self, url):
        self._assert_file_installed(url)

        print('deleting stored content for: ' + url)

        file_metadata = self._file_metadata_dict[url]
        del self._file_metadata_dict[url]

        os.unlink(file_metadata.get_file_path())
        self._delete_data(file_metadata, url)

        print('deleted stored content for: ' + url)

    def delete_all_files(self):
        for url in self.all_file_urls():
            self.delete_file(url)

    def get_etag_for_file(self, url):
        return self._file_metadata_dict[url].etag
    
    def get_file_stream(self, url):
        return open(self._get_file_path(url), 'r')

    # Methods to override to add data storage

    def _get_metadata_cls(cls):
        return FileMetadata

    def _install_data_from_file(self, url):
        pass

    def _load_data_from_stored(self):
        pass

    def _store_data(self):
        pass

    def _data_contains_url(self, url):
        pass

    def _update_metadata_from_file(self, url):
        pass

    def _delete_data(self, file_metadata, url):
        pass
