## 1 finds the median value
You are interested in analyzing some hard-to-obtain data from two separate databases. Each database contains n numerical values, so there are \\(2n\\) values total and you may assume that no two values are the same. You’d like to determine the median of this set of \\(2n\\) values, which we will define here to be the nth smallest value.

However, the only way you can access these values is through queries to the databases. In a single query, you can specify a value k to one of the two databases, and the chosen database will return the \\(k^{th}\\) smallest value that it contains. Since queries are expensive, you would like to compute the median using as few queries as possible.

Give an algorithm that finds the median value using at most \\(O(log n)\\) queries.

### solution
if mid D1 < mid D2 \\(T(D1,D2) = T(higher D1, lower D2)\\)

or else \\(T(D1,D2) = T(higher D2, lower D1)\\)

```python
function findMedia(D1,D2)
    p1,p2 = n/2
    for i = 2 to log(n)
        m1 = query(D1, p1)
        m2 = query(D2, p2)
        if m1 > m2 then
            p1 = p1 - n/2^i
            p2 = p2 + n/2^i
        else
            p1 = p1 + n/2^i
            p2 = p2 + n/2^i
    end for
    return min(m1,m2)
end function
```

### correctness & complexity
Every time the two databases D1 and D2 will be set half and half, and we can make sure that the final result is between the 2 middle value of D1 and D2.

The problem is \\(T(n) = T(n/2) + 2c\\), so the time complexity is \\(O(log(n))\\)

## 2 find \\(k^{th}\\) largest element
Find the \\(k^{th}\\) largest element in an unsorted array. Note that it is the \\(k^{th}\\) largest element in the sorted order, not the k th distinct element. \
__INPUT__: An unsorted array A and k. \
__OUTPUT__: The \\(k^{th}\\) largest element in the unsorted array A.

```python
function KTH(A[], low, high, k)
    t = partition(A, low , high) // partition the same as quick-sort
    if t==k then
        return A[t] //found
    else if t<k then
        return KTH(A,t,high,k) // find in the right area
    else
        return KTH(A,low,t,k) // find in the left area
end function
```
### correctness & complexity
The partition in quicksort can divide the elements to 2 parts, and the \\(k^{th}\\) elements will be set to the exact \\(k^{th}\\) position. The left values are all smaller then it, and the righ values are bigger. So the \\(k^{th}\\) elements will finally be found.

__good situation__

if the area is divided half and half, then \\(T(n) = n + n/2 + ... + 1 = 2n\\), so complexity is \\(O(n)\\)

__bad situation__

if the area is divided 1 and n-1 each time, then \\(T(n) = n + (n-1) + ... + 1 = n(n-1)/2 \\), so complexity is \\(O(n^2)\\)

## 3 tree minimum local node
Consider an n-node complete binary tree T, where \\(n = 2d − 1\\) for some d. Each node v of T is labeled with a real number \\(x^v\\). You may assume that the real numbers labeling the nodes are all distinct. A node v of T is a local minimum if the label \\(x^v\\) is less than the label \\(x^w\\) for all nodes w that are joined to v by an edge.

You are given such a complete binary tree T, but the labeling is only specified in the following implicit way: for each node v, you can determine the value \\(x^v\\) by probing the node v. Show how to find a local minimum of T using only \\(O(log n)\\) probes to the nodes of T.

```python
function TreeLocalMin(T)
    if probe(T.root) <= probe(T.left) and probe(T.root) <= probe(T.right) then
        return T
    else if probe(T.root) >= probe(T.left) then
        return TreeLocalMin(T.left)
    return TreeLocalMin(T.right)
end function
```

### correctness
1. if T is bigger then left and right child, then T is the local minimum one .

2. else if left is smaller then root, then the left child tree must have a satisfied node, because at least the minimum one of left tree must satisfy.

3. so as right according 2

the problem is \\(T(n) = T(n/2) + c\\), the levels of the tree is equal to the query counts. So the complexity is \\(O(log(n))\\).

## 4 minimum node of matrix
Suppose now that you’re given an \\(n × n\\) grid graph G. (An \\(n × n\\) grid graph is just the adjacency graph of an \\(n × n\\) chessboard. To be completely precise, it is a graph whose node set is the set of all ordered pairs of natural numbers (i, j), where \\(1 <= i <= n\\) and \\(1 <= j <= n\\); the nodes (i, j) and (k, l) are joined by an edge if and only if \\(|i − k| + |j − l| = 1\\).)

We use some of the terminology of problem 3. Again, each node v is labeled by a real number \\(x^v\\); you may assume that all these labels are distinct. Show how to find a local minimum of G using only \\(O(n)\\) probes to the nodes of G. (Note that G has n 2 nodes.)

### solution
1. divide G to 4 parts with 2 lines, the middle row and the middle column, and find the minimum value of the 6 border lines, called V

2. judge if V is the minimum local one, if not find the one that is smaller then V from node adjacent to V, called W

3. the subproblem is the the square of the 4 parts where W is in.

### correctness
if the minimum node V satisfy then return V, if not, let the square that W is in called square A, so W will be smaller then V, while V is smaller then the border of A, so W is smaller then the border of A, so there must be a solution in the square A.

the problem is \\(T(n) = T(n/2) + 6n\\), so the time complexity will be \\(O(n)\\)

## 5 divide convex polygon to triangles
Given a convex polygon with n vertices, we can divide it into several separated pieces, such that every piece is a triangle. When n = 4, there are two different ways to divide the polygon; When n = 5, there are five different ways.

Give an algorithm that decides how many ways we can divide a convex polygon with n vertices into triangles.

### solution
choose an edge AB of the polygon, then choose the other vertex \\(P_1,...,P_k\\), which do not contains A and B, to form a triangle, the triangle will divide the polygon to 2 parts, then we only have to solve the 2 sub polygons.

```python
function convex(n)
    sum = 0
    if n <= 3 then
        return 1
    for k = 2 to n-1
        sum = sum + convex(k) * convex(n-k+1)
    return sum
end function
```

### correctness
As has described, the polygon will be divided to 2 sub polygons, because we choose the decided edge and different vertex, so the middle triangle will be unique, so the situation will be no repeated.

because every n polygons will be divided to n-1 sub problem, so the complexity is \\(O(n^2)\\)

## 6 find number of inversions
Recall the problem of finding the number of inversions. As in the course, we are given a sequence of n numbers \\(a_1, · · · , a_n\\), which we assume are all distinct, and we define an inversion to be a pair \\(i < j\\) such that \\(a_i > a_j\\) .

We motivated the problem of counting inversions as a good measure of how different two orderings are. However, one might feel that this measure is too sensitive. Let’s call a pair a significant inversion if \\(i < j\\) and \\(a_i > 3a_j\\) . Given an \\(O(n log n)\\) algorithm to count the number of significant inversions between two orderings.

### solution
use merge-sort to divide the array
```python
function inverse(A)
    L = A[1...n/2], R = A[n/2+1,...,n]
    M = inverse(L)
    N = inverse(R)
    MN = merge(L,R)
    return M + N + MN
end function

function merge(L, R)
    i,j = 1,1
    sum = 0
    for k in 1 to n
        if L[i] > R[j] then
            A[k] = L[i]
            i++
            if L[i] > 3*R[j] then
                sum += i
        else
            A[k] = R[j]
            j++
    end for
    return sum
end function
```

### correctness
the algorithm is expanded by the normal inverse numbers algorithm, we only change the condition to \\(a_i > 3a_j\\), so it is correct.

the complexity is the same as the merge sort, \\(T(n) = 2*T(n/2) + cn\\) so the complexity is \\(O(nlog(n))\\)
