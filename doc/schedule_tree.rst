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

A `union map` can be *splitted* into a `band map`, or simply a `band`. A
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

`band maps` are extended to `trees maps` or simply `trees`. A `tree` behaves
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

Canonic Tree
------------

A _canonic_ tree can be extracted from the C source code, using labels to
identify parts of the tree::

    void foo(int N, float x[N][N], float y[N][N]) {
        for(int i=0; i<N; i++)
    L0:     for(int j=0; j<N; j++)
    S0:         x[i][j] = x1[i][j]*2

        for(int i=0; i<N; i++)
            for(int j=0; j<N; j++)
    S1:         y[i][j] = x[i][j] + y[j][i];
    }

All non-loop instructions have to be given a label, used to name the schedule
input space. Labeled loops are used to decide to split a band into several
nodes. In the above example, the first loop nest is splitted into two nodes
because the inner loop is named, while the second loop nest is not splitted
because it receives no label::

    { S0[i,j] -> [i] } # anonymous
        { S0[i,j] -> [j] } : L0
    { S1[i,j] -> [i,j] } # anonymous


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

    fuse(tree, node_or_node_name, *node_or_names_to_fuse, name=None, out=None)

    >>> t = isl.Tree('''
    { S0[i,j] -> [i] ; S1[i,j] -> [i] ; S2[i,j] -> [i]} : A
        { S0[i,j] -> [j] } : B
        { S2[i,j] -> [] }
        { S1[i,j] -> [j] } : C
    ''')

    >>> fuse(t, 'A', 'B', 'C', name='D')
    { S0[i,j] -> [i] ; S1[i,j] -> [i] ; S2[i,j] -> [i]} : A
        { S0[i,j] -> [j] ; S1[i,j] -> [j] } : D
        { S2[i,j] -> [] }

    >>> fuse(t, 'A', 'B', 'C', name='D', out='C')
    { S0[i,j] -> [i] ; S1[i,j] -> [i] ; S2[i,j] -> [i]} : A
        { S2[i,j] -> [] }
        { S0[i,j] -> [j] ; S1[i,j] -> [j] } : D

`*node_or_names_to_fuse` must be direct children of `node_or_node_name`. They
are fused into the first node of `*node_or_names_to_fuse` that receives the
given `name`. `out` is the child position of the fused node. It is set to the
first node of `*node_or_names_to_fuse` if not given another value, that must
still belong to `*node_or_names_to_fuse`.

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

This sections lists several interactive session using `trees` to perform common
transformations.

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

The above scenario makes looks simpler in Object-Oriented form::

    >>> t['C1'].interchange([1,0])
    >>> t['R'].fuse('C0', 'C1', name='F')
    >>> t['F'].tile((4,4), names=('G',))

Note that in that case, all modifications are done in place.



`gemver` from the polybench is a more complex case. The input code is the following::

    void kernel_gemver(int n, double alpha, double beta,
        double A[n][n],
        double u1[n], double v1[n], double u2[n], double v2[n],
        double w[n], double x[n], double y[n], double z[n])
    {
    C0: for(int i = 0; i < n; i++)
          for (int j = 0; j < n; j++)
    S0:     A[i][j] = A[i][j] + u1[i] * v1[j] + u2[i] * v2[j];

    C1: for(int i = 0; i < n; i++)
          for (int j = 0; j < n; j++)
    S1:     x[i] = x[i] + beta * A[j][i] * y[j];

    C2: for(int i = 0; i < n; i++)
    S2:   x[i] = x[i] + z[i];

    C3: for(int i = 0; i < n; i++)
          for (int j = 0; j < n; j++)
    S3:     w[i] = w[i] + alpha * A[i][j] * x[j];
    }

The associated initial schedule tree could be::

    >>> print t
    {S0[i,j] -> [] ; S1[i,j] -> [] ; S2[i] -> []  ; S3[i,j] -> []}
        { S0[i,j] -> [i,j] } : C0
        { S1[i,j] -> [i,j] } : C1
        { S2[i] -> [i] } : C2
        { S3[i,j] -> [i,j] } : C3
    >>> t.name = 'R'

First we want to interchange the loops from `S1`, which can be done using::

    >>> t['C1'].interchange([1,0])
    >>> print t
    {S0[i,j] -> [] ; S1[i,j] -> [] ; S2[i] -> []  ; S3[i,j] -> []} : R
        { S0[i,j] -> [i,j] } : C0
        { S1[i,j] -> [j,i] } : C1
        { S2[i] -> [i] } : C2
        { S3[i,j] -> [i,j] } : C3

Then we have to partially merge all loops together. Let's start by merging `C0` and `C1`::

    >>> t['R'].fuse('C0', 'C1', name='F0')
    >>> print t
    {S0[i,j] -> [] ; S1[i,j] -> [] ; S2[i] -> []  ; S3[i,j] -> []} : R
        { S0[i,j] -> [i,j] ; S1[i,j] -> [j,i]} : F0
            { S0[i,j] -> [] }
            { S1[i,j] -> [] }
        { S2[i] -> [i] } : C2
        { S3[i,j] -> [i,j] } : C3

Then we can tile `F0`, `C2` and `C3`::

    >>> t['F0'].tile([4,4], name='T0')
    >>> t['C2'].tile([4], name='T2')
    >>> t['C3'].tile([4,4], name='T3')
    >>> print t
    {S0[i,j] -> [] ; S1[i,j] -> [] ; S2[i] -> []  ; S3[i,j] -> []} : R
        { S0[i,j] -> [i,ip] : ... ; S1[i,j] -> [j,jp] : ...} : F0
            { S0[i,j] -> [j,jp] : ... ; S1[i,j] -> [i,ip] : ...} : T0
                { S0[i,j] -> [] }
                { S1[i,j] -> [] }
        { S2[i] -> [i, ip] : ... } : C2
        { S3[i,j] -> [i,ip] : ...} : C3
            { S3[i,j] -> [j,jp] : ...} : T3

Then fuse again::

    >>> t['R'].fuse('F0', 'C2', 'C3', name='F1')
    >>> print t
    {S0[i,j] -> [] ; S1[i,j] -> [] ; S2[i] -> []  ; S3[i,j] -> []} : R
        { S0[i,j] -> [i,ip] : ... ; S1[i,j] -> [j,jp]: ... ; S2[i] -> [i,ip]: ... ; S3[i,j] -> [i,ip]: ...  } : F1
            { S0[i,j] -> [j,jp]: ...  ; S1[i,j] -> [i,ip]: ... } : T0
                { S0[i,j] -> [] }
                { S1[i,j] -> [] }
            { S2[i] -> [] } : C2
            { S3[i,j] -> [j,jp] : ... } : T3


`normalize_sample` is a benchmark extracted from the mlp application. The original, inlined C code is the following::

    static void normalizeSample(int subImageRows, int subImageCols,
                                int imageRows, int imageCols,
                                uint8_t image[imageRows][imageCols],
                                int imageOffsetRow, int imageOffsetCol,
                                int resultRows, int resultCols,
                                float resultArray[resultRows][resultCols])
    {
          /* meanChar { */
    S0:   float sum = 0;

    L0:   for (int i = 0; i < subImageRows; i++)
    L1:     for (int j = 0; j < subImageCols; j++) {
    S1:       sum += image[i + imageOffsetRow][j + imageOffsetCol];
            }

    S2:   float sampleMean = sum / (subImageRows * subImageCols);
          /* } */

          /* minChar { */
    S3:   uint8_t minvalue = 255;

    L2:   for (int i = 0; i < subImageRows; i++)
    L3:     for (int j = 0; j < subImageCols; j++)
    S4:       minvalue = min(minvalue, image[i + imageOffsetRow][j+imageOffsetCol]);

    S5:   float sampleMin  = minvalue;
          /* } */

          /* maxChar { */
    S6:   uint8_t maxvalue = 0;

    L4:   for (int i = 0; i < subImageRows; i++)
    L5:     for (int j = 0; j < subImageCols; j++)
    S7:       maxvalue = max(maxvalue, image[i + imageOffsetRow][j+imageOffsetCol]);

    S8:   float sampleMax = maxvalue;
          /* } */

    S9:   sampleMax -= sampleMean;
    S10:  sampleMin -= sampleMean;

    S11:  sampleMax = fmaxf(fabsf(sampleMin), fabsf(sampleMax));

    S12:  if (sampleMax == 0.0)
            sampleMax = 1.0;

          /* convertFromCharToFloatArray { */
    S13:  float quotient = 1.0 / sampleMax ,
                shift = -(1.0 / sampleMax) * sampleMean;
    L6:   for (int i = 0; i < resultRows; i++)
    L7:     for (int j = 0; j < resultCols; j++)
    S14:      resultArray[i][j] = quotient * (float)image[i + imageOffsetRow][j + imageOffsetCol] + shift;
          /* } */
    }


The associated canonical schedule tree is::

    >>> print t
    { S0[] -> [] ; S1[i,j] -> [] ;  S2[] -> [] ; S3[] -> [] ; S4[i,j] -> [] ; S5[] -> [] ; S6[] -> [] ; ... } : R
        { S0[] -> [] }
        { S1[i,j] -> [i] } : L0
            { S1[i,j] -> [j] } : L1
        { S2[] -> [] }
        { S3[] -> [] }
        { S4[i,j] -> [i] } : L2
            { S4[i,j] -> [j] } : L3
        { S5[] -> [] }
        { S6[] -> [] }
        { S7[i,j] -> [i] } : L4
            { S7[i,j] -> [j] } : L5
        { S8[] -> [] }
        { S9[] -> [] }
        { S10[] -> [] }
        { S11[] -> [] }
        { S12[] -> [] }
        { S13[] -> [] }
        { S14[i,j] -> [i] } : L6
            { S14[i,j] -> [j] } : L7


The main optimization one can do on this file is to fuse `S1`, `S4` and `S7`, but to do first have to permute a few statements::

    >>> t['R'][1], t['R'][2], t['R'][3], t['R'][4], t['R'][5], t['R'][6] = t['R'][2], t['R'][3], t['R'][5], t['R'][6], t['R'][1], t['R'][4]
    >>> print t
        { S0[] -> [] }
        { S2[] -> [] }
        { S3[] -> [] }
        { S5[] -> [] }
        { S6[] -> [] }
        { S1[i,j] -> [i] } : L0
            { S1[i,j] -> [j] } : L1
        { S4[i,j] -> [i] } : L2
            { S4[i,j] -> [j] } : L3
        { S7[i,j] -> [i] } : L4
            { S7[i,j] -> [j] } : L5
        { S8[] -> [] }
        { S9[] -> [] }
        { S10[] -> [] }
        { S11[] -> [] }
        { S12[] -> [] }
        { S13[] -> [] }
        { S14[i,j] -> [i] } : L6
            { S14[i,j] -> [j] } : L7

then we have to concatenate their respective band into a single node::

    >>> for n in ('S1', 'S4', 'S7'):
            t[n].cat()
    >>> print t
    { S0[] -> [] ; S1[i,j] -> [] ;  S2[] -> [] ; S3[] -> [] ; S4[i,j] -> [] ; S5[] -> [] ; S6[] -> [] ; ... } : R
        { S0[] -> [] }
        { S2[] -> [] }
        { S3[] -> [] }
        { S5[] -> [] }
        { S6[] -> [] }
        { S1[i,j] -> [i,j] } : L0
        { S4[i,j] -> [i,j] } : L2
        { S7[i,j] -> [i,j] } : L4
        { S8[] -> [] }
        { S9[] -> [] }
        { S10[] -> [] }
        { S11[] -> [] }
        { S12[] -> [] }
        { S13[] -> [] }
        { S14[i,j] -> [i] } : L6
            { S14[i,j] -> [j] } : L7


finally we can fuse them::

    >>> t['R'].fuse('L0', 'L2', 'L4', name='F0')
    >>> print t
    { S0[] -> [] ; S1[i,j] -> [] ;  S2[] -> [] ; S3[] -> [] ; S4[i,j] -> [] ; S5[] -> [] ; S6[] -> [] ; ... } : R
        { S0[] -> [] }
        { S2[] -> [] }
        { S3[] -> [] }
        { S5[] -> [] }
        { S6[] -> [] }
        { S1[i,j] -> [i,j] ; S4[i,j] -> [i,j] ; S7[i,j] -> [i,j] } : F0
        { S8[] -> [] }
        { S9[] -> [] }
        { S10[] -> [] }
        { S11[] -> [] }
        { S12[] -> [] }
        { S13[] -> [] }
        { S14[i,j] -> [i] } : L6
            { S14[i,j] -> [j] } : L7


The following example is extracted from the paper *Maximum Loop Distribution and Fusion for Two-level Loops Considering Code Size*::

    R:  for(int i=0; i<N; ++i) {
    L0:     for(int j=0;j<M; ++j) {
    S0:         A[i][j]=J[i−1][j]+5;
    S1:         B[i][j]=A[i][j]*3;
            }
    L1:     for(int j=0;j<M;++j) {
    S2:         C[i][j]=A[i−1][j]+7;
    S3:         D[i][j]=C[i][j−1]*2;
    S4:         E[i][j]=D[i][j]+B[i][j+2];
            }
        }

Its canonical tree is::

    >>> print t
    {S0[i,j]->[i] ; S1[i,j]->[i]; S2[i,j]->[i]; S3[i,j]->[i]; S4[i,j]->[i]; S5[i,j]->[i]; S6[i,j]->[i]; S7[i,j]->[i] } : R
        { S0[i,j]->[j] ;  S1[i,j]->[j] } : L0
            {S0[i,j] -> [] }
            {S1[i,j] -> [] }
        { S2[i,j]->[j] ;  S3[i,j]->[j] ;  S4[i,j]->[j] } : L1
            {S2[i,j] -> [] }
            {S3[i,j] -> [] }
            {S4[i,j] -> [] }

To maximize locality, we have to distribute loop `L1`, then fuse part of it with previous Loop. So first we distribute them::

    >>> t['L1'].distribute(t['L1'][2], names=('D0',))
    >>> print t
    {S0[i,j]->[i] ; S1[i,j]->[i]; S2[i,j]->[i]; S3[i,j]->[i]; S4[i,j]->[i]; S5[i,j]->[i]; S6[i,j]->[i]; S7[i,j]->[i] } : R
        { S0[i,j]->[j] ;  S1[i,j]->[j] } : L0
            {S0[i,j] -> [] }
            {S1[i,j] -> [] }
        { S2[i,j]->[j] ;  S3[i,j]->[j] } : L1
            {S2[i,j] -> [] }
            {S3[i,j] -> [] }
        { S4[i,j]->[j] } : D0
            {S4[i,j] -> [] }

Then we perform the fusion::
    >>> t['R'].fuse('L0', 'L1', name='F0')
    >>> print t
    {S0[i,j]->[i] ; S1[i,j]->[i]; S2[i,j]->[i]; S3[i,j]->[i]; S4[i,j]->[i]; S5[i,j]->[i]; S6[i,j]->[i]; S7[i,j]->[i] } : R
        { S0[i,j]->[j] ;  S1[i,j]->[j]; S2[i,j]->[j] ;  S3[i,j]->[j] } : F0
            {S0[i,j] -> [] }
            {S1[i,j] -> [] }
            {S2[i,j] -> [] }
            {S3[i,j] -> [] }
        { S4[i,j]->[j] } : D0
            {S4[i,j] -> [] }

And we manually get the same output as the original paper.
