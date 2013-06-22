===========================
ISL schedule tree extension
===========================

ISL provides `maps` and `union maps` as a way to map statement iterations to
schedule times. For instance::

    { S[i,j] -> L[i,j] }

maps iterations of the domain `S` to times of the domain `L`. Transforming such
maps leads to new iteration <> time mapping that may leads to statement
reordering.

Schedule trees, or `tree maps` provides a way to describe and manipulate
partial `union maps`.

Schedule trees are implemented as a Python layer over ISL, so Python syntax is
used throughout this document.

Bands
-----

A `union map` can be *splitted* into a `union band`, or simply a `band`. A
`band` is a list of *nodes*. Each node holds a *partial schedule* in the form of
a `union map` that shares the same iteration domain as the original one. The
concatenation of the time domains of each node of the band yields the time
domain of the original `union map`::

    { S[i,j] -> L[i,0,j] : i>=0 }

is equivalent to the followings bands::

    { S[i,j] -> L[i] : i>=0 }
        { S[i,j] -> [0] }
            { S[i,j] -> [j] }


    { S[i,j] -> L[i,0] : i>=0 }
        { S[i,j] -> [j] }


Note that the constraint applies to all the element of a `band` but is not
duplicated among them.

Two operations are defined on a band:

- `split(node, index)` turns the `node` of a `band` of time dimension greater or
  equal than `index` into a new band with an extra node. The original node gets a
  time dimension of `index` and the new node is inserted right after it and olds
  the remaining dimensions::

    >>> split('{ S[i,j] -> L[i,0,j] : i>=0 }', 2)
    { S[i,j] -> L[i,0] : i>=0 }
        { S[i,j] -> [j] }

- `cat(node, depth=-1)` concatenates a node with its `depth` successors, where
  `-1` means all successors::

    >>> band = isl.Band('''
    { S[i,j] -> L[i,0] : i>=0 }
        { S[i,j] -> [j] }
    ''')
    >>> cat(band, 1)
    { S[i,j] -> L[i,0,j] : i>=0 }

Each node of a band can have an optional name::

    { S[i,j] -> L[i,0] : i>=0 } : A
        { S[i,j] -> [j] } : B

The name can be used to refer to the node directly through the `__getitem__`
method::

    >>> band = isl.Band('''
    { S[i,j] -> L[i,0] : i>=0 } : A
        { S[i,j] -> [j] } : B
    ''')
    >>> band['B']
    { S[i,j] -> [j] } : B
     

Trees
-----

`Union bands` are extended to `union trees` or simply `trees`. A `tree` behaves
as a `band` except each node can have several children. The children are ordered
and this ordering represents an implicit time domain. For instance the following
`union map`::

    { S0[i,j] -> [i,0,j] ; S1[i,j] -> [i,1,j]}

Can be turned into the `band`::

    { S0[i,j] -> [i] ; S1[i,j] -> [i] }
        { S0[i,j] -> [0,j] ; S1[i,j] -> [1,j] }

Which can itself be represented as a `tree`::

    { S0[i,j] -> [i] ; S1[i,j] -> [i] }
        { S0[i,j] -> [j] }
        { S1[i,j] -> [j] }

The three above representation defines the same mapping.

If all the nodes of a `tree` have a single child, then the `tree` is a `band`.

Similarly to the nodes of a `band`, the nodes of a `tree` can be named and
retrieved through their name. Additionally, they can be retrieved from their
parents through integer indexing::

    >>> tree = isl.Tree('''
    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A
        { S0[i,j] -> [j] } : B
        { S1[i,j] -> [j] } : C
    ''')
    >>> tree['A'][0] is tree['B']
    True

Tree Properties
---------------

Any node of a `tree` can hold extra pieces of information in the form of
`properties`. There is an implicit property held by any node: the *sequential*
property. Eventually, the *parallel* property can be set *instead*. 

The children of a *sequential* node are ordered sequentially using and implicit
time domain as described above. The children of a *parallel* node do not hold
this extra time dimension. They are represented as::

    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A [parallel]
            { S0[i,j] -> [j] } : B
            { S1[i,j] -> [j] } : C

Note that it does not make sense to refer to children of a parallel node through
integer indexing.

Other pieces of information, such as code generation options, can be attached to
a node and used by the relevant function.


Tree Transformations
--------------------

Thanks to their recursive structure, `trees` are well suited for partial
transformations of a schedule. A general function is provided to transform a
given node of a tree::

    apply(tree, node_or_node_name, isl_union_map)

This function takes a `tree` and a way to identify a node in this tree through
an instance of the node or its name `node_or_node_name` and transforms the
partial schedule of this node using the given `isl_union_map`. A new tree is
returned as the result of this transformation, leaving the original tree
untouched.

For instance::

    >>> t = isl.Tree('''
    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A
            { S0[i,j] -> [j] }
            { S1[i,j] -> [j] }
    ''')
    >>> apply(t, t[1], isl.union_map('{[j] -> [j+1]}'))
    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A
            { S0[i,j] -> [j] }
            { S1[i,j] -> [j+1] }

Note that the leaves are left unchanged, which demonstrates the interest of the
tree representation that allows fro partial manipulation of the schedules.


Several functions are provided to make it easier to use common transformations.

Loop interchange is expressed as follows::

    interchange(tree, node_or_node_name, dimension_permutation)

    >>> t = isl.Tree('''
    { S0[i,j,k,l] -> [i,j,k] } : A
            { S0[i,j,k,l] -> [l] }
    ''')
    >>> interchange(t, 'A', (2, 0, 1))
    { S0[i,j,k,l] -> [k,i,j] } : A
            { S0[i,j,k,l] -> [] }''')

If the length of `dimension_permutation` is lower than the number of dimensions
of the time domain of the selected node, the remaining dimensions are untouched.

Index set splitting is expressed as follows::

    index_set_split(tree, node_or_node_name, isl_union_map, names=None)

    >>> t = isl.Tree('''
    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A
        { S0[i,j] -> [j] } : B
        { S1[i,j] -> [j] } : C
    ''')

    >>> index_set_split(t, 'B', isl.union_map('{[i] -> [i] : i < 4}'))
    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A
        {} : B
            { S0[i,j] -> [j] : i < 4}
            { S0[i,j] -> [j] : i >= 4}
        { S1[i,j] -> [j] } : C

    >>> index_set_split(t, 'B', isl.union_map('{[i] -> [i] : i < 4}'), names=('C','D'))
    { S0[i,j] -> [i] ; S1[i,j] -> [i] } : A
        {} : B
            { S0[i,j] -> [j] : i < 4} : C
            { S0[i,j] -> [j] : i >= 4} :D
        { S1[i,j] -> [j] } : C

`isl_union_map` is used to partition the time domain. This transformation
creates two new nodes. The optional `names` argument makes it possible to give
names to these node

Tiling is expressed as follows::

    tile(tree, node_or_node_name, tile_sizes, names=None)

    >>> t = isl.Tree('''
    { S0[i,j] -> [i,j] ; S1[i,j] -> [i,j] } : A
        { S0[i,j] -> [] } : B
        { S1[i,j] -> [] } : C
    ''')

    >>> tile(t, 'A', [4,8], names=('D',))
    { S0[i,j] -> [ip,k] : 0<=k<4 & 4*ip + k = i ; S1[i,j] -> [ip,k] : 0<=k<4 & 4*ip + k = i } : A
        { S0[i,j] -> [jp,l] : 0<=l<4 & 4*jp + l = j; S1[i,j] -> [jp,l] : 0<=l<4 & 4*jp + l = j}  : D
            { S0[i,j] -> [] } : B
            { S1[i,j] -> [] } : C

*Note*: This only allows rectangular tiling...


The two following transformations are parametrized by several nodes.

Loop fusion is expressed as follows::

    fuse(tree, node_or_node_name, *node_or_names_to_fuse, name=None)

    >>> t = isl.Tree('''
    { S0[i,j] -> [i] ; S1[i,j] -> [i] ; S2[i,j] -> [i]} : A
        { S0[i,j] -> [j] } : B
        { S2[i,j] -> [] }
        { S1[i,j] -> [j] } : C
    ''')

    >>> fuse(t, 'A', 'B', 'C', name= 'D')
    { S0[i,j] -> [i] ; S1[i,j] -> [i] ; S2[i,j] -> [i]} : A
        { S0[i,j] -> [j] ; S1[i,j] -> [j] } : D
        { S2[i,j] -> [] }

`*node_or_names_to_fuse` must be direct children of `node_or_node_name`. They
are fused into the first node of `*node_or_names_to_fuse` that receives the
given `name`. 

*Note* this is a limited version of loop fusion...

Loop distribution is expressed as follows::

    distribute(tree, node_or_node_name, *node_or_names_to_distribute, names=None)
            
    >>> t = isl.Tree('''
    { S0[i,j] -> [i] ; S1[i,j] -> [i] ; S2[i,j] -> [i]} : A
        { S0[i,j] -> [j] } : B
        { S2[i,j] -> [] }
        { S1[i,j] -> [j] } : C
    ''')
    
    >>> distribute(t, 'A', 'B', 'C', names=('D', 'E'))
    { S0[i,j] -> [i] } : D
        { S0[i,j] -> [j] } : B
    { S2[i,j] -> [i]} : A
        { S2[i,j] -> [] }
    { S1[i,j] -> [i] } : E
        { S1[i,j] -> [j] } : C


Examples
--------

This sections lists several (currently one) interactive session using `trees` to
perform common transformations.

The original code, extracted from the PLUTO paper, is a succession of
matrix-vector multiply and transposed matrix-vector multiply::

    void foo(int N, float x1[N], float y1[N], float x2[N], float y2[N]) {
        for(int i=0; i<N; i++)
            for(int j=0; j<N; j++)
                S0:           x1[i] = x1[i] + a[i][j]∗y1[j];

        for(int i=0; i<N; i++)
            for(int j=0; j<N; j++)
                S1:          x2[i] = x2[i] + a[j][i]∗y2[j];
    }

This code can be turned into polyhedral form and we get the associated
sequential schedule in the form of a `tree`::

    >>> print t
    {S0[i,j] -> [] ; S1[i,j] -> []} : R
        { S0[i,j] -> [i,j] } : C0
        { S1[i,j] -> [i,j] } : C1

First step consists in interchanging the two dimensions of `C1` to prepare for
the fusion::

    >>> t_0 = interchange(t, 'C1', [1,0])
    >>> print t_0
    {S0[i,j] -> [] ; S1[i,j] -> []} : R
        { S0[i,j] -> [i,j] } : C0
        { S1[i,j] -> [j,i] } : C1

Then, we want to fuse `C0` and `C1` to improve locality::

    >>> t_1 = fuse(t_0, 'R', 'C0', 'C1', name='F')
    >>> print t_1
    {S0[i,j] -> [] ; S1[i,j] -> []} : R
        {S0[i,j] -> [i,j] ; S1[i,j] -> [j,i]} : F
            { S0[i,j] -> [] } : C0
            { S1[i,j] -> [] } : C1

Eventually, we want to tile `R` for even more locality::

    >>> t_2 = tile(t_1, 'F', (4,4), names=('G',))
    >>> print t_2
    {S0[i,j] -> [] ; S1[i,j] -> []} : R
        {S0[i,j] -> [it,ip] : 0<=ip<4 & i = 4*it + ip; S1[i,j] -> [jt, jp] : 0<=jp<4 & j = 4*jt + jp} : F
            {S0[i,j] -> [jt, jp] : 0<=jp<4 & j = 4*jt + jp ; S1[i,j] -> [it, ip] : 0<=ip<4 & i = 4*it + ip} : G
                { S0[i,j] -> [] } : C0
                { S1[i,j] -> [] } : C1
