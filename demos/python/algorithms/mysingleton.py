#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''实现单例模式的几种方法'''

'''
方法一
Python 的模块就是天然的单例模式，因为模块在第一次导入时，会生成 .pyc 文件，当第二次导入时，就会直接加载 .pyc 文件，而不会再次执行模块代码。因此，我们只需把相关的函数和数据定义在一个模块中，就可以获得一个单例对象了。如果我们真的想要一个单例类，直接在其他文件中导入此文件中的对象，这个对象即是单例模式的对象
'''
'''
class Singleton(object):
    def foo(self):
        pass

singleton = Singleton()

# 此处导入的singleton就是个单例模式的对象
from a import singleton
'''

'''
方法二
使用装饰器
'''
'''
def Singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)

        return _instance[cls]

    return _singleton

@Singleton
class A(object):
    a = 1

    def __init__(self, x=0):
        self.x = x


a1 = A(2)
a2 = A(3)
print a1.x      # 2
print a2.x      # 2
print a1 == a2  # True
# 因为a1在生成的时候初始化为self.x = 2, a2生成是并没有调用__init__，所以self.x还是2，a1，a2属于同一个对象
'''


'''
方法三
使用类，并使用线程加锁，解决多线程情况下产生多个对象的问题
'''
'''
import time
import threading

class Singleton(object):
    _instance_lock = threading.Lock()

    def __init__(self):
        pass

    @classmethod
    def instance(self, *args, **kwargs):
        if not hasattr(Singleton, '_instance'):
            with Singleton._instance_lock:
                if not hasattr(Singleton, '_instance'):
                    Singleton._instance = Singleton(*args, **kwargs)

        return Singleton._instance


def task(arg):
    obj = Singleton.instance()
    print obj

for i in range(10):
    t = threading.Thread(target=task, args=[i,])
    t.start()

time.sleep(20)
obj = Singleton.instance()
print obj
'''

'''
方法四
基于__new__方法实现
'''
'''
import threading


class Singleton(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(Singleton, "_instance"):
            with Singleton._instance_lock:
                if not hasattr(Singleton, "_instance"):
                    Singleton._instance = object.__new__(cls)

        return Singleton._instance

    def __init__(self):
        pass

obj1 = Singleton()
obj2 = Singleton()
print obj1, obj2

def task(args):
    obj = Singleton()
    print obj

for i in range(10):
    t = threading.Thread(target=task, args=[i,])
    t.start()
'''

'''
方法五
基于metaclass方法实现
1.类由type创建，创建类时，type的__init__方法自动执行，类() 执行type的 __call__方法(类的__new__方法,类的__init__方法)
2.对象由类创建，创建对象时，类的__init__方法自动执行，对象()执行类的 __call__ 方法
'''

import threading


class SingletonType(type):
    _instance_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if not hasattr(SingletonType, "_instance"):
            with SingletonType._instance_lock:
                if not hasattr(SingletonType, "_instance"):
                    SingletonType._instance = super(SingletonType, cls).__call__(*args, **kwargs)
        return cls._instance

# python 2实现
class Foo():
    __metaclass__ = SingletonType

    def __init__(self, name):
        self.name = name

# python 3实现
class Foo(metaclass=SingletonType):
    def __init__(self, name):
        self.name = name

f1 = Foo("zhangsan")
f2 = Foo("lisi")
print f1.name
print f2.name
print f1 == f2