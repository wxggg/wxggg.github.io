本文主要介绍了b/b+树的特点以及为什么b/b+树在数据库中应用广泛，另外介绍了b/b+树基本操作的c++实现，并附完整源代码

## 一、 b树和b+树
__共同点：__ 首先b/b+树每个节点能够保存多个关键字，数量上限为M-1，这里M为b/b+树的度，限制了键的数量和子节点的数目，当一个非叶子节点有n个键的时候，必定有n+1个子节点。

其次节点内及节点间的键值按顺序排列

除根节点外的其它节点最少有 ceil(M/2)-1 个关键字

__不同点：__ b树的每个节点都既能保存键(Key)又能保存值(Value)，而b+树只有叶子节点能够保存值，内部节点只保存键和子节点的指针

b+树叶节点采用链表结构

## 二、 为什么用b/b+树
数据库如MySQL的数据一般放在磁盘中，而读盘的过程包括两次机械运动盘片旋转和磁头移动，这一过程比较耗时，所以对数据的访问性能受限于访问磁盘的次数。

b/b+树相对于其他搜索树如平衡二叉树和红黑树能够明显减少索引次数，b/b+树的特点是单个节点能够保存很多键，所以保存相同数量的的键和值内容时，b系树的高度要明显小于二叉查找树，所以b系树访问磁盘的次数也要更小。

## 三、为什么b+树比b树更适合做数据库索引
首先b+树的磁盘读写代价更低，因为b+树的内部节点不保存值（Value），所以相同大小的硬盘数据块能够保存更多的索引关键字，因而读写次数更少。

b+树的查询更加稳定，因为只有叶节点保存值，所以每次查询的路径长度相同，并且因为b+树的叶节点通过链表进行链接，所以在遍历数据时更加方便，相对而言的b树完整顺序遍历所有数据则需要进行中序遍历。

而且因为b+树的叶节点通过链表链接，所以可以很容易进行范围查询

## 四、实现
这里介绍b/b+树的C++实现，为了简化这里的实现只考虑在内存中(In Memory)的访问数据的情况

### 1. 节点结构
考虑到b和b+树的节点存在相似性，采用如下的数据结构作为b/b+树的基本节点，其中保存了无论是内部节点还是叶子节点都需要的数据，包括关键字和子节父节点的指针，对于b+树而言，base_node可以直接作为其内部节点使用。
```c++
template <class Key, class Value, size_t M=20>

struct base_node { // 作为b树节点的父类，同时作为b+树的内部节点
    Key key[M]; // M-1 at most
    base_node *child[M+1]; // M at most
    base_node *parent;
    size_t n;
};
```
b树的节点和b+树的叶节点都还需要保存value，并且b+树的叶节点还需要进行链接，所以采用如下设计：
```c++
struct btree_node : public base_node { // 作为b树的节点
    Value value[M];
};

struct bplus_leaf_node : public btree_node { // 作为b+树的叶节点
    bplus_leaf_node * next;
};
```

### 2. 查找
首先无论是数据的增删改查都离不开对键的查找，b树和b+树的查找类似二叉树，区别在于b系树先找到节点之后然后在对有序数组进行二分查找，根据查找的结果确定子节点的链接

需要区别的就是对于b树的查找，查找到的每个节点都可能是要找的节点，而b+树一定要查找到叶节点

### 3. 插入
b树和b+树的插入有所不同，首先b树可能在树的某一个节点就插入了数据，而b+树插入是一定要插入到叶节点中。相同的是在某个节点插入了新的数据之后，需要判断节点的数量是否已满，如果已经超过了节点数量上限M-1，需要对节点进行分裂调整。

首先如下是b树的插入操作，在查找到相应的节点之后，判断节点中该key是否已经存在，是的话就直接返回，否则进行key和value的插入，然后调整节点的数量，对于达到M的节点进行分裂

需要注意的是b树在分裂时需要将key和value都进行分裂，而且还要将子节点child也进行分裂，分裂的另一部分都分配给新增的另一节点newnode，这里值得注意的是分配给分裂的子节点需要设置新的parent

在b树节点分裂的过程中会将中间的一个节点挪到父节点中，这样会导致父节点中插入新的key、value，所以需要继续调整父节点
```c++
void btree::insert(Key k, Value v)
{
    auto p = search(k); // 找到要插入的节点
    if (binary_serach(p, k)) return; 

    p->insert(k,v) // 插入 k,v 到b树节点
    p->n++;

    while(p != root && p->n == M)
        split(p); // 如果节点键超过上限，分裂节点
        p = p->parent; // 继续调整父节点
}
```

b+树的插入操作需要考虑内部节点和叶子节点的区别，首先在插入k,v时如果插入成功是一定会插入到叶节点的，如果叶子节点的数目达到上限，也需要进行分裂

b+树的叶子节点的分裂与b树的不同在于，b+树将中间的数据复制到父节点，而不从两个子节点中删除

b+树内部节点也会因为子节点的分裂而导致数据增加，因此依然需要从子节点往上遍历调整父节点的关键字数目

### 4. 删除
键和值的删除相对比较麻烦，在删除的过程中节点会因为关键字太少而需要调整，b/b+树的非叶子节点都需要满足节点数不少于 ceil(M/2)-1 个，所以在删除的过程中存在一系列的节点调整操作，如果当前节点数过少且旁边的兄弟节点有多余的关键字的话，就需要从兄弟节点借一个过来，如果兄弟节点没有多余的话那么可以选择和兄弟节点合并为一个节点，当然在这种情况下新节点的数目是不会超过M-1的

首先看b树的删除操作，b树在删除键值对时首先仍然需要进行查找，如果没找到当然不用删了，找到了之后也不是就直接删除该处的值。对于叶节点，可以直接删除节点中的键值对，但是对于内部节点，为了避免因内部节点关键字的缺少而引起树的结构发生变化，采用将该内部节点的要删除的key的后继key挪过来。
```c++
void btree::remove(Key k)
{
    auto p = search(k);
    int i = lower_bound(p, k); // 找到要删除的位置
    if(!p->isleaf()) // 如果当前节点不是叶节点
        find pnext //找到后继key对应的键值对覆盖要删除的位置
        p = pnext

    p->remove(i);
    p->n--;

    while(p != root && p->n < BORDER) // BORDER = ceil(M/2)-1 
        brother = left or right // 找到左右兄弟节点，借一个或者合并
        if (brother->n > BORDER) borrow(p, brother);
        else merge(p, brother) 
        p = p->parent;
}
```

b+树不存在从内部节点删除键值对的问题，因为删除只能是从叶子节点开始的，但是b+树需要考虑叶节点和内部节点在borrow和merge时的操作有所不同。进行叶节点的borrow或merge，要操作的对象包括key、value，而内部节点的borrow或merge则需要考虑key和child的问题。最后需要要注意的是，在内部节点borrow和merge的过程中，都需要考虑child的parent的问题，要重新设置child的parent。

### 5. 完整代码

b树和b+树实现完整代码请参考 [https://github.com/wxggg/algorithm/blob/master/include/btree.hh](https://github.com/wxggg/algorithm/blob/master/include/btree.hh)

## 五、参考
[1] [B树和B+树的插入、删除图文详解](https://www.cnblogs.com/nullzx/p/8729425.html)

[2] [为什么MySQL数据库索引选择使用B+树？](https://www.cnblogs.com/tiancai/p/9024351.html)

[3] [MySQL索引背后的数据结构及算法原理](http://blog.codinglabs.org/articles/theory-of-mysql-index.html)

[4] [利用c/c++ 开发基于B+树的小型关系型数据库](http://www.enpeizhao.com/?p=905)

[5] [BPlusTree: B+树实现-磁盘存取](https://github.com/zcbenz/BPlusTree)

[6] [https://github.com/wxggg/algorithm](https://github.com/wxggg/algorithm)