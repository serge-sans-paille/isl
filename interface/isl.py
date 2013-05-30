'''
The module provides a python-friendly wrapper to the Integer Set Library.

In a similar way to sympy, users can manipulate named identifiers, known as Symbols
>>> Symbol('a')
a

And one can build multiple Symbols out of a sequence
>>> symbols('A b C')
(A, b, C)

The empty set is built with no parameters
>>> Set()
{  }

The universal set is parametrized by a predicate that always yields true
>>> Set(lambda:True)
{  :  }

Which gives another way to build the empty set
>>> Set(lambda:False)
{  }

A set can be generated through an iterator over some points
>>> Set(i for i in range(1,6) if i != 4)
{ [5]; [3]; [2]; [1] }

The set containing the whole 0-dimensional space is pretty similar too
>>> Set([])
{ [] }

A set can be defined through a n-arguments predicate
>>> Set(lambda i,j: i<j)
{ [i, j] : j >= 1 + i }

The function predicate manipulates extended sympy expressions, see http://docs.sympy.org/0.6.7/modules/logic.html
>>> Set(lambda i,j: (2 < i) & (i < 10) )
{ [i, j] : i >= 3 and i <= 9 }

Any function that returns a boolean and manipulates sympy expression can be used as a predicate, although lambda expressions are generally enough.
>>> def foo(i,j):
...    a = 2 < i 
...    b = j <10
...    return a & b
>>> Set(foo)
{ [i, j] : i >= 3 and j <= 9 }

A Predicate can refer to non-local named symbols
>>> import operator
>>> n = Symbol('n')
>>> Set(lambda  i, j : reduce(operator.and_, ( 0 < i , i <= n, 0 < j, j <= i) ) )
[n] -> { [i, j] : i >= 1 and i <= n and j >= 1 and j <= i }

A predicate can make use of the exists operator
>>> n =Symbol('n')
>>> Set( lambda i: exists(lambda a: (a == (3*i)) & (a == (2*i)) & (i <n) )  )
[n] -> { [0] : n >= 1 }

exists can be nested from increased fun.
>>> Set( lambda i: exists(lambda a: (3*a == i) & exists(lambda b: 2*b == a ) ) )
{ [i] : exists (e0 = [(i)/3], e1 = [(i)/6]: 3e0 = i and 6e1 = i) }

The space associated to a set can be named.
>>> n =Symbol('n'); T = Symbol('T')
>>> Set(lambda i: (T[i], (0 < i) & (i<n)) )
[n] -> { T[i] : i >= 1 and i <= -1 + n }

There can be multiple name definitions at once
>>> n = Symbol('n') ; T,F,B = symbols('T F B')
>>> Set(lambda i: (T[i],0 < i) ,
...     lambda i: (F[i], 0 < i), 
...     lambda i: (B[i], (0 <= i) & (i < n) )
... )
[n] -> { T[i] : i >= 1; F[i] : i >= 1; B[i] : i >= 0 and i <= -1 + n }

basic set operations are supported:

union, through the `union' method or the + operator
>>> Set(lambda i,j: i>j) + Set(lambda i,j: i<j)
{ [i, j] : j <= -1 + i or j >= 1 + i }

intersection, through the `intersect' method
>>> n = Symbol('n')
>>> S = Set(lambda i: (0<i) & (i<n))
>>> T = Set(lambda i: n == 5)
>>> S.intersect(T)
[n] -> { [i] : n = 5 and i >= 1 and i <= 4 }

Test if a set is empty or not
>>> bool(Set(lambda i,j: (0<j)&(j<2)))
True
>>> 'has something' if Set(lambda i:(i>1)&(i==-i)) else 'empty'
'empty'
'''

import isl_core as core
import inspect
import ctypes


def symbols(str_desc):
    '''
    Returns a list holding one Symbol per variable name in the string description,
    where the string description consists of whitespace-separated names.
    '''
    return tuple(Symbol(s) for s in str_desc.split(' ') if s)

class Symbol(object):
    '''
    A symbol is just an identifier representing an integer of unknown value
    or a named set, a named map...
    '''

    symbol_cache = {}

    def __init__(self, name):
        '''
        Symbol(name) -> new Symbol bound to a name.
        '''
        self.name = name
        Symbol.symbol_cache.setdefault(name,[]).append(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __getitem__(self, *indices):
        return self

    def dependencies(self):
        return {self}

unary_operator_printer = {
        '__neg__' : '-',
        }
operator_printer = {
        '__lt__' : '<',
        '__le__' : '<=',
        '__eq__' : '=',
        '__ne__' : '!=',
        '__ge__' : '>=',
        '__gt__' : '>',
        '__not__' : '!',
        '__and__' : 'and',
        '__or__' : 'or',
        '__add__' : '+',
        '__radd__' : '+',
        '__sub__' : '-',
        '__rsub__' : '-',
        '__mul__' : '*',
        '__rmul__' : '*',
        '__div__' : '/',
        '__rdiv__' : '/',
        }

reversed_operators = {
        '__radd__',
        '__rsub__',
        '__rmul__',
        '__rdiv__'
        }

def new_operator(op):
    return lambda self, other: Operator(op, self, other)
def new_unary_operator(op):
    return lambda self: UnaryOperator(op, self)

# Just too lazy to write all operators overload by hand
for op in operator_printer.iterkeys():
    setattr(Symbol, op, new_operator(op))
for op in unary_operator_printer.iterkeys():
    setattr(Symbol, op, new_unary_operator(op))

class Value(object):
    '''
    A Value is an abstract representation of a particular literal.
    When using an integer in an expression, they are automatically promoted to Value.
    '''

    def __init__(self, value):
        '''
        Value(literal) -> new Value holding the literal
        '''
        self.value = value

    def __str__(self):
        return str(self.value)

    def dependencies(self):
        return set()


class Operator(Symbol):
    '''
    An Operator represents any binary operation on Symbols and Values.
    Basically, they are a mean to build an AST at runtime.
    '''

    def __init__(self, op, lhs, rhs):
        '''
        Operator(op, lhs, rhs) -> abstract representation of `lhs op rhs'.
        '''
        super(Operator, self).__init__(op)
        self.lhs = lhs if isinstance(lhs, Symbol) else Value(lhs)
        self.rhs = rhs if isinstance(rhs, Symbol) else Value(rhs)
        if op in reversed_operators:
            self.lhs, self.rhs = self.rhs, self.lhs

    def __str__(self):
        return '({0} {1} {2})'.format(
                self.lhs,
                operator_printer[self.name],
                self.rhs
                )
    __repr__ = __str__

    def dependencies(self):
        return set.union(
                self.lhs.dependencies(),
                self.rhs.dependencies()
                )

class UnaryOperator(Symbol):
    '''
    An UnaryOperator represents any unary operation on Symbols and Values.
    Basically, they are a mean to build an AST at runtime.
    '''

    def __init__(self, op, rhs):
        '''
        UnaryOperator(op, rhs) -> abstract representation of `op rhs'.
        '''
        super(UnaryOperator, self).__init__(op)
        self.rhs = rhs if isinstance(rhs, Symbol) else Value(rhs)

    def __str__(self):
        return '({0} {1})'.format(
                unary_operator_printer[self.name],
                self.rhs
                )
    __repr__ = __str__

    def dependencies(self):
        return self.rhs.dependencies()

class FormalSymbol(Symbol):
    '''
    A FormalSymbol is a Symbol that does not live in the global space.
    As a consequence, it is ignored when building an AST dependencies.
    '''

    def dependencies(self):
        return set()

# a few hackish method injection
core.union_set.__repr__ = core.union_set.__str__
core.union_set.__add__ = core.union_set.union
core.union_set.__sub__ = core.union_set.subtract
core.union_set.__contains__ = lambda self, point: bool(self.intersect(Set([point])))
core.union_set.__nonzero__ = lambda self : not self.is_empty()
core.union_map.__call__ = lambda self, other: other.apply(self) if isinstance(other, core.union_set) else other.apply_range(self)
core.union_map.__repr__ = core.union_map.__str__

def Set(*values):
    '''
    Set() -> the empty set
    Set(iterable_sequence) -> the set containing all integers in the iterable_sequence
    Set(predicate) -> the integer set defined by this predicate
    Set(*predicates) -> the union of the sets defined by the predicates
    '''

    def format_predicate(exp):
        '''
        Convenient helper to turn a predicate into a string.
        '''
        if isinstance(exp, bool):
            return ' ' if exp else '0 = 1'
        else:
            return str(exp)

    dependencies = set()

    # empty set
    if len(values) == 0:
        content = '{ }'

    # set from values
    elif len(values) == 1 and  hasattr(values[0], '__iter__'):
        values = list(values[0])
        # gather dependencies and normalize types
        for i,v in enumerate(values):
            if hasattr(v, '__iter__'):
                for k in v:
                    if hasattr(k, 'dependencies'):
                        dependencies.update(k.dependencies())
                values[i] = list(v)
            else:
                if hasattr(v, 'dependencies'):
                    dependencies.update(v.dependencies())
                values[i] = [v]
        if values:
            content = '{{ {0} }}'.format("; ".join("{0}".format(value) for value in values))
        else:
            content = '{ [ ] }'
    # set from predicates
    else:
        content = list()
        dependencies = set()
        for value in values:
            assert inspect.isfunction(value), 'Set argument is callable'
            code = value.__code__
            argument_identifiers = code.co_varnames[:code.co_argcount]
            argument_symbols = (FormalSymbol(i) for i in argument_identifiers)
            evaluation = value(*argument_symbols)
            if isinstance(evaluation, tuple):
                space_name , evaluation = evaluation
            else:
                space_name = ''

            value_content='{0} : {1}'.format(
                    '{0}[{1}]'.format(
                        space_name,
                        ', '.join(argument_identifiers)
                        ) if argument_identifiers else '',
                    format_predicate(evaluation)
                    )
            if hasattr(evaluation, 'dependencies'):
                dependencies.update(evaluation.dependencies())
            content.append(value_content)

        content = '{{ {0} }}'.format("; ".join(content))

    if dependencies:
        content = '[{0}] -> {1}'.format(
                    ', '.join(map(str,dependencies)),
                    content
                    )

    return core.union_set(content)

def Map(*values):
    '''
    Map(mapping) -> a map that performs the association defined by the mapping.
    Map(*mapping) -> the union of the maps defined by the mappings.

    A mapping is a n-ary function that yields a k-ary predicate
    '''
    def format_predicate(exp):
        '''
        Convenient helper to turn a predicate into a string.
        '''
        if isinstance(exp, bool):
            return ' ' if exp else '0 = 1'
        else:
            return str(exp)
    content = list()
    dependencies = set()
    for value in values:
        assert inspect.isfunction(value), 'Set argument is callable'
        code = value.__code__
        argument_identifiers = code.co_varnames[:code.co_argcount]
        argument_symbols = (FormalSymbol(i) for i in argument_identifiers)
        evaluation = value(*argument_symbols)
        if isinstance(evaluation, Symbol):
            evaluation = (evaluation,)
        if len(evaluation) != 2 or all(isinstance(x, Symbol) for x in evaluation):
            output_identifiers = evaluation
            predicate = None
        else:
            output_identifiers, predicate = evaluation

        value_content='[{0}] -> [{1}] {2}'.format(
                ', '.join(map(str,argument_identifiers)) if argument_identifiers else '',
                ', '.join(map(str,output_identifiers)) if output_identifiers else '',
                (': ' + format_predicate(predicate)) if predicate else ''
                )
        if hasattr(predicate, 'dependencies'):
            dependencies.update(predicate.dependencies())
        content.append(value_content)

    content = '{{ {0} }}'.format("; ".join(content))

    if dependencies:
        content = '[{0}] -> {1}'.format(
                    ', '.join(map(str,dependencies)),
                    content
                    )

    return core.union_map(content)


class exists(Operator):
    '''
    Special kind of predicate that return True for all elements that match a given constraint.
    As all other Operators, it is just a proxy to build the AST.
    '''

    def __init__(self, constraint):
        '''
        exists(constraint) -> proxy operator
        '''
        code = constraint.__code__
        argument_identifiers = code.co_varnames[:code.co_argcount]
        argument_symbols = (FormalSymbol(i) for i in argument_identifiers)
        evaluation = constraint(*argument_symbols)
        self.content = 'exists {0}: {1}'.format(
                ','.join(map(str,argument_identifiers)),
                evaluation
                )

        self.deps = evaluation.dependencies()

    def __str__(self):
        return self.content

    def dependencies(self):
        return self.deps

if __name__ == '__main__':
    import doctest
    res = doctest.testmod()
    import sys
    sys.exit(res.failed)
