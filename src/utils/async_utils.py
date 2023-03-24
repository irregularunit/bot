"""
 * Bot for Discord
 * Copyright (C) 2023 Irregular Unit
 * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
 * For more information, see README.md and LICENSE
"""

import inspect
from abc import ABCMeta

__all__: tuple = ("AsyncObject",)


class AsyncABCMeta(ABCMeta):
    def __init__(cls, name, bases, methods):
        coros = {}
        for base in reversed(cls.__mro__):
            coros.update((name, val) for name, val in vars(base).items() if inspect.iscoroutinefunction(val))

        for name, val in vars(cls).items():
            if name in coros and not inspect.iscoroutinefunction(val):
                raise TypeError('Must use async def %s%s' % (name, inspect.signature(val)))
        super().__init__(name, bases, methods)


class AsyncABC(metaclass=AsyncABCMeta):
    pass


class AsyncInstanceType(AsyncABCMeta):
    @staticmethod
    def __new__(cls, clsname, bases, attributes):
        if '__init__' in attributes and not inspect.iscoroutinefunction(attributes['__init__']):
            raise TypeError('__init__ must be a coroutine')
        return super().__new__(cls, clsname, bases, attributes)

    async def __call__(cls, *args, **kwargs):
        self = cls.__new__(cls, *args, **kwargs)
        await self.__init__(*args, **kwargs)
        return self


class AsyncObject(metaclass=AsyncInstanceType):
    pass
