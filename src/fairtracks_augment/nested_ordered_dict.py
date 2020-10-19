# Expanded from github.com/fairtracks/fairtracks_standard
# Ref: https://github.com/fairtracks/fairtracks_augment/issues/23

from collections import OrderedDict
from typing import Iterable


def _is_iterable(item):
    return isinstance(item, Iterable) and not isinstance(item, str)


class NestedOrderedDict(OrderedDict):
    """
    OrderedDict that automatically enlarges itself when needed. Also if an
    iterable is provided as the key, this is interpreted as a path, i.e.
    ```
    nestedDict[['a', 'b']] == nestedDict['a']['b']
    ```
    """

    def get(self, item, default=None):
        if _is_iterable(item):
            cur_dict = self
            for key in item:
                cur_dict = cur_dict.get(key, default)
                if cur_dict is default:
                    break
            return cur_dict
        else:
            return super().get(item, default)

    def __getitem__(self, item):
        if _is_iterable(item):
            cur_dict = self
            for key in item:
                cur_dict = cur_dict.__getitem__(key)
            return cur_dict
        else:
            return super().__getitem__(item)

    def __setitem__(self, item, data):
        if _is_iterable(item):
            cur_dict = self
            last_i = len(item) - 1
            for i, key in enumerate(item):
                if i == last_i:
                    break
                if key not in cur_dict:
                    cur_dict.__setitem__(key, NestedOrderedDict())
                cur_dict = cur_dict.__getitem__(key)
            cur_dict.__setitem__(key, data)
        else:
            if isinstance(data, dict):
                data = NestedOrderedDict(data)
            elif _is_iterable(item):
                data = [NestedOrderedDict(_) if isinstance(_, dict) else _
                        for _ in data]
            super().__setitem__(item, data)
