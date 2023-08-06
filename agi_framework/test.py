

class B:
    def foo(self):
        super().foo()
        print ('B.foo()')

class C:
    def foo(self):
        print ('C.foo()')

class A(B, C):
    def foo(self):
        super().foo()
        print ('A.foo()')

a = A()
a.foo()
print(A.__mro__)
