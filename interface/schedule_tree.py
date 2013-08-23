from isl import core as isl

TABSPACE = 8

import ply.lex as lex
tokens = (
        'PARTIAL_SCHEDULE',
        'SPACE',
        'NL',
        'PARTIAL_SCHEDULE_NAME',
        )

t_NL = r'[\n\r]+'

def t_SPACE(t):
    r'[ \t]+'
    s = t.value
    t.value = s.count(' ') + TABSPACE * s.count('\t')
    return t

def t_PARTIAL_SCHEDULE(t):
    r'\{[^}]*\}[ \t]*'
    um = t.value
    t.value = isl.union_map(um)
    return t

def t_PARTIAL_SCHEDULE_NAME(t):
    r'[ \t]*:[ \t]*[a-zA-Z][a-zA-Z0-9_]*'
    psn = t.value
    import re
    t.value = re.sub(r'[ \t:]','', psn)
    return t

def t_error(t):
    raise RuntimeError("error when parsing schedule tree")

class Tree(object):

    def __init__(self, relation, *children, **kwargs):
        if type(relation) is str:
            self.from_string(relation)
        else:
            self.relation = relation
            self.children = list(children)
            self.name = kwargs.get('name',None)

    @staticmethod
    def lex(lexer, level):
        tok = lexer.next()
        while tok.type == 'NL':
            tok = lexer.next()
        assert tok.type == 'PARTIAL_SCHEDULE', tok.type
        relation = tok.value
        name = None
        children = []
        try:
            tok = lexer.next()
            while tok:
                if tok.type == 'PARTIAL_SCHEDULE_NAME':
                    name = tok.value
                    tok = lexer.next()
                elif tok.type == 'SPACE':
                    if level < tok.value:
                        nlevel = tok.value
                        tree, tok = Tree.lex(lexer, nlevel)
                        children.append(tree)
                    else:
                        break
                elif tok.type == 'NL':
                    tok = lexer.next()
                else:
                    assert False
        except StopIteration:
            tok = None
            pass
        return Tree(relation, *children, name=name), tok

    def from_string(self, s):
        lexer = lex.lex()
        lexer.input(s)
        tree, _ = Tree.lex(lexer, 0)
        self.relation = tree.relation
        self.children = tree.children
        self.name = tree.name

    def get_new_name(self):
        import random, string
        res = ''
        names = [x.name for x in self.children] + ['']
        while res in names:
            res = ''.join(random.choice(string.uppercase) for x in range(1+len(self.children)/10))
        return res



    def __str__(self, depth=0):
        if depth:
            prelude = ' ' * TABSPACE * depth 
        else:
            prelude = ''
        return prelude + str(self.relation) + ( ': {}'.format(self.name) if self.name else '' ) + ''.join('\n'+x.__str__(depth+1) for x in self.children)

    def __getitem__(self, index):
        if type(index) is str:
            if index == self.name: return self
            else: return filter(lambda x:x.name ==index, self.children)[0]
        return self.children[index]

    def __setitem__(self, index, value):
        self.children[index] = value

    def split(self, n_dim, front_name='', back_name=''):
        heads = []
        tails = []
        def foo(x):
            assert n_dim < x.n_out()
            front = isl.union_map('{{ {3}[{0}] -> {2}[{1}]}}'.format(
                ','.join('_{0}'.format(i) for i in xrange(x.n_out())),
                ','.join('_{0}'.format(i) for i in xrange(n_dim)),
                front_name or x.out_space_name(),
                x.out_space_name()
                )
                )

            back = isl.map('{{ {3}[{0}] -> {2}[{1}]}}'.format(
                        ','.join('_{0}'.format(i) for i in xrange(x.n_out())),
                        ','.join('_{0}'.format(i) for i in xrange(n_dim, x.n_out())),
                        back_name,
                        x.out_space_name()
                        )
                        )
            tails.append(back(x))
            heads.append(front(x))
            return 1

        self.relation.foreach_map(foo)


        tail = Tree(reduce(isl.union_map.union, tails, isl.union_map('{}')), *self.children)
        self.relation = reduce(isl.union_map.union, heads, isl.union_map('{}'))
        self.children = [tail]

        return self


    def cat(self, depth=-1):
        if depth == -1:
            depth=0
            curr = self
            while len(curr.children) == 1:
                depth +=1
                curr = curr.children[0]
        curr = self
        relations = []
        for i in xrange(depth):
            relations.append(curr.relation)
            assert len(curr.children) == 1
            curr = curr.children[0]
        relations.append(curr.relation)
        relations = filter(lambda x:not isl.union_map.is_empty(x), relations)
        self.relation = reduce(isl.union_map.flat_range_product, relations)
        self.children = curr.children
        return self


    def interchange(self, dimension_permutation):
        relations = []
        def foo(x):
            if len(dimension_permutation) < x.n_out():
                perms = list(dimension_permutation) + range(len(dimension_permutation), x.n_out())
            else:
                perms = dimension_permutation
            transfo = isl.map(
                    '{{ {2}[{0}] -> {2}[{1}]}}'.format(
                        ','.join('_{0}'.format(i) for i in xrange(x.n_out())),
                        ','.join('_{0}'.format(i) for i in perms),
                        x.out_space_name()
                        )
                        )
            relations.append(transfo(x))

        self.relation.foreach_map(foo)
        self.relation = reduce(isl.union_map.union, relations, isl.union_map('{}'))
        return self

    def copy(self):
        return Tree(isl.union_map(self.relation), *[x.copy for x in self.children])

    def index_set_split(self, splitter, names=None):
        first_relations = []
        second_relations = []
        def foo(x):
            negate = isl.map(
                    '{{ {2}[{0}] -> {2}[{1}] : {3} }}'.format(
                        ','.join('_{0}'.format(i) for i in xrange(x.n_out())),
                        ','.join('__{0}'.format(i) for i in xrange(x.n_out())),
                        x.out_space_name(),
                        ' and '.join('_{0} != __{0}'.format(i) for i in xrange(x.n_out()))
                        )
                        )
            first_relations.append(splitter(x))
            second_relations.append(x.subtract(splitter(x)))

        self.relation.foreach_map(foo)
        self.relation = isl.union_map('{}')
        new_relations = [
                reduce(isl.union_map.union, first_relations, isl.union_map('{}')),
                reduce(isl.union_map.union, second_relations, isl.union_map('{}'))
                ]
        if names is None:
            names = []
        names = list(names)
        names.extend([None] * (2-len(names)))
        self.children = [
                Tree(new_relations[0], *[x.copy() for x in self.children], name=names[0]),
                Tree(new_relations[1], *[x.copy() for x in self.children], name=names[1]),
                ]
        return self

    def tile(self, tile_sizes, name=None):
        relations_outer = []
        relations_inner = []
        def foo(x):
            tsizes = list(tile_sizes)
            tsizes.extend([1] * (x.n_out() - len(tsizes)))
            transfo = isl.map(
                    '{{ {2}[{0}] -> {2}[{1}] : {3}}}'.format(
                        ','.join('_{0}'.format(i) for i in xrange(x.n_out())),
                        ','.join('__{0}'.format(i) for i in xrange(x.n_out())),
                        x.out_space_name(),
                        ' and '.join('__{0} mod {1} = 0 and __{0} <= _{0} < __{0} + {1}'.format(x,y) for x,y in zip(xrange(x.n_out()), tsizes)),
                        )
                    )
            relations_outer.append(transfo(x))
            relations_inner.append(x)
        self.relation.foreach_map(foo)

        self.relation = reduce(isl.union_map.union, relations_outer, isl.union_map('{}'))
        self.children = [Tree(reduce(isl.union_map.union, relations_inner, isl.union_map('{}')), *self.children, name=name)]
        return self

    def fuse(self, *targets, **kwargs):
        name = kwargs.get('name', None)
        out = kwargs.get('out', 0)
        targets = [t if type(t) is Tree else self[t] for t in targets]
        targets_relation = [t.relation for t in targets]
        targets_children = [t.children for t in targets]
        print targets_children
        fused_relation = reduce(isl.union_map.union, targets_relation, isl.union_map('{}'))
        fused_children = []
        map(fused_children.extend, targets_children)
        for i, n in enumerate(list(self.children)):
            if out in (i, n, n.name):
                self.children[i] = Tree(fused_relation, *fused_children, name=name)
        for n in targets:
            try:
                self.children.remove(n)
            except ValueError:
                pass
        return self

    def distribute(self, *targets, **kwargs):
        names = kwargs.get('names', [])
        if not names:
            names = []
        names = list(names)
        targets = [t if type(t) is Tree else self[t] for t in targets]
        names.extend([None]*(len(targets)-len(names)))

        distributed = {}
        filtered_out = set()

        for target in targets:
            target_relation = []
            def foo(x):
                target_relation.append(x)
            target.relation.foreach_map(foo)
            assert len(target_relation) == 1, "there must be only one map in target {}".format(target.name)
            target_relation = target_relation[0]

            selector = isl.map(
                    '{{ {2}[{0}] -> {2}[{1}] }}'.format(
                        ','.join('_{0}'.format(i) for i in xrange(target_relation.n_in())),
                        ','.join('__{0}'.format(i) for i in xrange(target_relation.n_in())),
                        target_relation.in_space_name()
                        )
                    )
            distributed[target] = self.relation(selector)
            filtered_out.add(target_relation.in_space_name())

        kept_relations = []
        empty_relations = []
        def foo(x):
            if x.in_space_name() not in filtered_out:
                kept_relations.append(x)
            empty_relations.append(isl.map('{{{0}[{1}] -> {2}[]}}'.format(
                x.in_space_name() or '',
                ','.join('_{0}'.format(i) for i in xrange(x.n_in())),
                x.out_space_name() or ''
                )
                )
                )

        self.relation.foreach_map(foo)


        new_nodes = []
        for node in self.children:
            if node in distributed:
                new_nodes.append(Tree(distributed[node], node, name=names.pop(0)))
            else:
                new_nodes.append(Tree(reduce(isl.union_map.union, kept_relations, isl.union_map('{}')), node, name=self.name))

        self.relation = reduce(isl.union_map.union, empty_relations, isl.union_map('{}'))
        self.children = new_nodes
        self.name = None
        return self

    def flat(self, index=0):
        self_relations = []
        def foo(x):
            transfo = isl.map(
                    '{{ {2}[{0}] -> {2}[{1}]}}'.format(
                        ','.join('_{0}'.format(i) for i in xrange(x.n_out())),
                        ','.join([str(index)] + ['_{0}'.format(i) for i in xrange(x.n_out())]),
                        x.out_space_name(),
                        )
                        )
            self_relations.append(transfo(x))
        self.relation.foreach_map(foo)
        children_relations = []
        for i, child in enumerate(self.children):
            children_relations.append( child.flat(i) )
        all_self_relations =  reduce(isl.union_map.union, self_relations,  isl.union_map('{}'))
        if children_relations:
            all_children_relations = reduce(isl.union_map.union,children_relations, isl.union_map('{}'))
            return reduce(isl.union_map.flat_range_product, [all_self_relations, all_children_relations])
        else:
            return all_self_relations







