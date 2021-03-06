"""
─────────────────────────────────────────────────────────────────────────────────────────────────────
─██████████████─██████████████───████████──████████─██████─────────██████████████─████████──████████─
─██░░░░░░░░░░██─██░░░░░░░░░░██───██░░░░██──██░░░░██─██░░██─────────██░░░░░░░░░░██─██░░░░██──██░░░░██─
─██░░██████████─██░░██████░░██───████░░██──██░░████─██░░██─────────██░░██████░░██─████░░██──██░░████─
─██░░██─────────██░░██──██░░██─────██░░░░██░░░░██───██░░██─────────██░░██──██░░██───██░░░░██░░░░██───
─██░░██─────────██░░██──██░░██─────████░░░░░░████───██░░██─────────██░░██████░░██───████░░░░░░████───
─██░░██──██████─██░░██──██░░██───────████░░████─────██░░██─────────██░░░░░░░░░░██─────████░░████─────
─██░░██──██░░██─██░░██──██░░██─────────██░░██───────██░░██─────────██░░██████████───────██░░██───────
─██░░██──██░░██─██░░██──██░░██─────────██░░██───────██░░██─────────██░░██───────────────██░░██───────
─██░░██████░░██─██░░██████░░████───────██░░██───────██░░██████████─██░░██───────────────██░░██───────
─██░░░░░░░░░░██─██░░░░░░░░░░░░██───────██░░██───────██░░░░░░░░░░██─██░░██───────────────██░░██───────
─██████████████─████████████████───────██████───────██████████████─██████───────────────██████───────
─────────────────────────────────────────────────────────────────────────────────────────────────────

Copyright (C) 2022 GQYLPY <http://gqylpy.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import threading


class GqylpyCache(type):
    __shared_instance_cache__ = False
    __not_cache__ = []

    def __new__(mcs, *a, **kw):
        if a[0].__class__ is GqylpyCache.__new__.__class__:
            return FunctionCaller(a[0])
        return type.__new__(mcs, *a, **kw)

    def __init__(cls, __name__: str, __bases__: tuple, __dict__: dict):
        __not_cache__: list = __dict__.get('__not_cache__')

        if __not_cache__:
            cls.delete_repeated(__not_cache__)
            cls.check_and_tidy_not_cache(__not_cache__, __dict__)
            cls.delete_repeated(__not_cache__)

        cls.__getattribute__ = __getattribute__(cls)

        if cls.__shared_instance_cache__:
            cls.__cache_pool__ = {}

        type.__init__(cls, __name__, __bases__, __dict__)

    def __call__(cls, *a, **kw):
        ins: cls = type.__call__(cls, *a, **kw)

        if not cls.__shared_instance_cache__:
            ins.__cache_pool__ = {}

        return ins

    def check_and_tidy_not_cache(cls, __not_cache__: list, __dict__: dict):
        not_found = []

        for index, name_or_method in enumerate(__not_cache__):
            if name_or_method.__class__ is str:
                name: str = name_or_method

                for x in cls.local_instance_dict_set():
                    if name == x:
                        break
                else:
                    name in not_found or not_found.append(name)
                    continue

                method = getattr(cls, name)

            else:
                method = name_or_method

                try:
                    name = __not_cache__[index] = method.__name__
                except AttributeError:
                    if method.__class__ in (staticmethod, classmethod):
                        name = __not_cache__[index] = method.__func__.__name__
                    elif method.__class__ is property:
                        name = __not_cache__[index] = method.fget.__name__
                    else:
                        name = name_or_method

                for x in cls.local_instance_dict_set(v=True):
                    if method == x:
                        break
                else:
                    name in not_found or not_found.append(name)
                    continue

            if not (
                    callable(method)
                    or method.__class__ in (property, staticmethod, classmethod)
            ):
                name in not_found or not_found.append(name)
                continue

        if not_found:
            x = f'{cls.__module__}.{cls.__name__}'
            e = not_found if len(not_found) > 1 else not_found[0]
            raise type('NotCacheDefineError', (Exception,), {'__module__': __package__}) \
                (f'The "{__package__}" instance "{x}" has no method "{e}".')

    @staticmethod
    def delete_repeated(data: list):
        index = len(data) - 1
        while index > -1:
            offset = -1
            while index + offset > -1:
                if data[index + offset] == data[index]:
                    del data[index]
                    break
                else:
                    offset -= 1
            index -= 1

    def local_instance_dict_set(cls, baseclass=None, *, v: bool = False):
        cur_cls: GqylpyCache or type = baseclass or cls

        if cur_cls.__class__ is GqylpyCache:
            yield from cur_cls.__dict__.values() if v else cur_cls.__dict__
            yield from cur_cls.local_instance_dict_set(cur_cls.__base__)

    class NotCacheDefineError(Exception):
        __module__ = __package__


class ClassMethodCaller:

    def __new__(cls, cls_: GqylpyCache, sget, name: str, method):
        if method.__class__ is property:
            __cache_pool__: dict = sget('__cache_pool__')

            try:
                cache: dict = __cache_pool__[name]
            except KeyError:
                cache = __cache_pool__[name] = {}
                cache['__exec_lock__'] = threading.Event()
                cache['__return__'] = sget(name)
                cache['__exec_lock__'].set()
            else:
                if '__exec_lock__' in cache:
                    cache['__exec_lock__'].wait()
                    del cache['__exec_lock__']

            return cache['__return__']

        return object.__new__(cls)

    def __init__(self, cls: GqylpyCache, sget, name: str, method):
        self.__cls = cls
        self.__sget = sget
        self.__name__ = name
        self.__func__ = method
        self.__qualname__ = method.__qualname__

    def __call__(self, *a, **kw):
        __cache_pool__: dict = self.__sget('__cache_pool__')
        key: tuple = self.__name__, a, str(kw)

        try:
            cache: dict = __cache_pool__[key]
        except KeyError:
            cache = __cache_pool__[key] = {}
            cache['__exec_lock__'] = threading.Event()
            cache['__return__'] = self.__sget(self.__name__)(*a, **kw)
            cache['__exec_lock__'].set()
        else:
            if '__exec_lock__' in cache:
                cache['__exec_lock__'].wait()
                del cache['__exec_lock__']

        return cache['__return__']

    def __str__(self):
        return f'{ClassMethodCaller.__name__}' \
               f'({self.__cls.__module__}.{self.__qualname__})'


class FunctionCaller:

    def __init__(self, func):
        self.__func__ = func
        self.__name__ = func.__name__
        self.__qualname__ = func.__qualname__
        self.__globals__ = func.__globals__
        self.__exec_lock__ = threading.Lock()
        self.__cache_pool__ = {}

    def __call__(self, *a, **kw):
        key = a, str(kw)

        self.__exec_lock__.acquire()
        if key not in self.__cache_pool__:
            self.__cache_pool__[key] = self.__func__(*a, **kw)
        self.__exec_lock__.release()

        return self.__cache_pool__[key]

    def __str__(self):
        return f'{FunctionCaller.__name__}' \
               f'({self.__func__.__module__}.{self.__qualname__})'


def __getattribute__(cls: GqylpyCache):
    def inner(ins: cls, attr: str):
        sget = super(cls, ins).__getattribute__

        if (
                attr in ('__cache_pool__', '__not_cache__') or
                attr in cls.__not_cache__ or
                attr not in cls.__dict__
        ):
            return sget(attr)

        value = getattr(cls, attr)

        if not (callable(value) or value.__class__ in (property, classmethod)):
            return sget(attr)

        return ClassMethodCaller(cls, sget, attr, value)

    return inner
