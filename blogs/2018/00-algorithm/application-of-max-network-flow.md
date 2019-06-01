##Load balance
You have some different computers and jobs. For each job, it can only be done on one of two specified computers. The load of a computer is the number of jobs which have been done on the computer. Give the number of jobs and two computer ID for each job. You task is to minimize the max load.
(hint: binary search)

Implement Ford-Fulkerson algorithm to find the maximum flow of the following network, and list your intermediate steps. Use you implementation to solve problem 1 and show your answers. INPUT: (N, M) means number of jobs and computers. Next N line, each line has two computer ID for a job. see more detial in the file problem1.data. OUTPUT: the minimum number of the max load.

```
#There are multiple data sets.
#For each data set, the first line has two number N and M, which means the number of jobs and the number of computers.
#Next N line, each line for a job, has two number which means the two computers.
4 2
1 2
1 2
1 2
1 2

7 49
31 49
42 21
31 37
2 44
28 10
43 7
8 48

...
```

### solution
Let the jobs collection be \\(J = {J_1, J_2, ..., J_m}\\) and computer set as \\(C = {C_1, C_2, ..., C_n}\\), and the two set can be two part of binary picture, so the job and computer mapping problem can be turned to a binary picture. In [0,jobnum] find the minimum capacity for computer to 'T',

* construct a binary picture:
  + add a vertex 'S' and 'T', 'S' connects with all Jobs and set capacity of each edge as 1
  + 'T' connects all Computers, initially set capacity to jobnum
  + connect the jobs to the computer that they belong to, and capacity is 1
* search the minimum maxload that can satisfy the jobs
  + 1.mid = (left+right)/2, clear the map and set computers capacity to mid
  + 2.use ford-fulkerson algorithm(use delta to scale) to get the maxflow
  + 3.compare the maxflow and jobnum, if equal set right = mid
  + 4.else not equal: set left = mid + 1
  + 5.continue step 1

__INPUT:__ \
a series of jobs and computers \
__OUTPUT:__ \
the minimum number of the max load
```c
function minMaxLoad(jobs[], computers[])
  network = NetworkFlow()
  //construct a network use jobs and computers
  //add vertex 's' and 't', set edge 's' to jobs capacity as 1
  //initially set computers to 't' capacity as jobnum
  left,right = 0,jobnum
  while left<right
    mid = (left+right)/2
    network.clear() // clear the flow to 0 of network
    for e in edge of the 't'
      set the reverse edge of e capacity to mid
    maxflow = network.maxFlow('s','t')
    if maxflow == jobnum
      right = mid
    else:
      left = mid + 1
  end while
  return left
end function
```

### correctness
* 1.use bi-search the [0,jobnum] area, because the jobnum can make sure that there must be at least one solution in the area, so we will find at least one maxload certainly.
* 2.if the mid of [a,b] do not generate a solution, then in [a,mid] does not exist any solution, find the other part
* 3.if mid does generate a solution, it means in [a,mid] there is at least a solution certainly

The delta-scaling Ford-Fulkerson complexity is \\(O(m^2log_2C)\\), and bi-search complexity is \\(O(log_2C)\\), so the total complexity is \\(O(m^2(log_2C)^2)\\)


[complete python program](/static/file/algorithm/networkflow1.py)



##Matrix
For a matrix filled with 0 and 1, you know the sum of every row and column. You are asked to give such a matrix which satisfys the conditions.

Implement push-relabel algorithm to find the maximum flow of a network, and list your intermediate steps. Use your implementation to solve problem 2 and write a check problem to see if your answer is right. INPUT: Numbers of rows and columns. And the sum of them. See more detial in the file problem2.data. OUTPUT: The matrix you get. Any one satisfy the conditions will be accept.

```
#There are multiple data sets.
#For each data set, the first line has two number M and N, which means the matrix is M*N.
#Next 2 line, the first line has M number, which indicate the sum of rows and the second line means the sum of columns.
10 10
5 5 7 7 6 3 5 7 7 3
6 6 7 4 5 6 6 4 4 7
13 14
10 5 7 6 4 7 8 9 9 8 6 10 5
8 7 6 8 5 2 6 8 8 5 10 7 5 9
120 110
60 52 61 63 54 52 53 49 57 56 56 58 59 57 52 60 58 49 62 60 63 58 56 55 60 56 58 49 46 59 62 61 55 51 64 55 60 57 60 57 47 63 57 58 53 55 47 67 52 56 51 52 55 58 55 54 55 58 61 50 58 64 59 57 48 44 54 53 42 57 54 66 58 56 64 51 56 53 56 56 53 51 49 54 58 56 48 60 55 54 57 53 54 59 54 42 62 63 58 52 48 64 49 65 47 65 59 47 57 58 45 45 63 64 61 63 54 55 49 54
63 62 57 64 60 58 48 54 54 60 60 56 69 63 61 66 64 53 57 50 61 68 53 67 57 68 58 60 63 61 66 66 63 64 63 58 64 63 67 66 55 61 60 57 63 65 61 56 60 60 65 63 63 57 53 59 64 56 62 53 56 58 60 65 56 59 62 70 64 65 62 61 57 65 67 63 65 60 61 69 53 61 66 55 67 64 64 61 67 59 62 58 62 47 55 54 63 57 64 58 57 61 53 66 69 64 59 61 65 59
23 57
33 26 25 38 25 26 28 31 24 28 25 36 28 32 29 32 29 23 25 28 27 26 26
```

### solution
Set every row as a vertex, and form a row collection \\(r = {r_1, r_2, ..., r_m}\\) and a column collection \\(c = {c_1, c_2, ..., c_n}\\), can be described as a network, add a total row source vertex 'S' and a total column target vertex 'T', then if the network have a maxflow == sum of the whole matrix, then there must exist a solution.

* construct a network with the row vertex and column vertex
  + the row vertex connects with the 'S', and capacity is the sum of each row
  + the column vertex connects with 'T', and capacity is the sum of each column
  + the row vertex connects with the column vertex, capacity is 1, so every position of the matrix is 1 or 0
* find a maxflow of the network
  + if maxflow == sum of the whole matrix, then there exist a solution
  + if not, there's no solution

__INPUT:__ \
the sum of rows and sum of columns\
__OUTPUT:__ \
a matrix satisfy the conditions
```c
function minMaxLoad(rows[], columns[])
  network = NetworkFlow()

  // add vertex 'S' and 'T'
  total = sum(rows)
  for i in range(m)
    network.addVertex(ri)
    network.addEdge('s', ri, rows[i])
  for i in range(n)
    network.addVertex(ci)
    network.addEdge(ci, 't', columns[i])
  for i in range(m)
    for j in range(n)
      // add edge of ri to ci
  maxflow = network.maxFlow('s', 't')
  if maxflow = total
    // the flow of each edge between rows and columns form the matrix
    return true
  else
    return false

end function
```

### correctness
* the capacity of the edge between the row vertex and the columns vertex is 1/0, which makes sure the value will only be 1 or 0, and the sum of rows and sum of columns forms the other edge
* if the network have a maxflow, and maxflow == the whole sum, then there must be a solution to the problem

The push-relabel algorithm complexity is \\(O(mn)\\), and to form the network the complexity is \\(O(mn)\\), so the total complexity is \\(O(2mn)\\)

[complete python program](/static/file/algorithm/networkflow2.py)



##Unique Cut
>Let G = (V, E) be a directed graph, with source s ∈ V , sink t ∈ V , and nonnegative edge capacities ce. Give a polynomial-time algorithm to decide whether G has a unique minimum st cut.

### solution
We can get a \\(G_fs\\) network by Ford-Fulkerson algorithm, use DFS to find the vertex collection that 's' can reach, and use DFS from 't' to find all the vertex collection that 't' can reach, if collection S and collection T is the same, then the cut is unique

__INPUT:__ \
G = (V, E) s,t \
__OUTPUT:__ \
whether the cut of G is unique
```c
G = maxflow(G)
function getCut(G, s, t)
  vertexs = DFS(G, s)
  vertext = DFS(G, t)
  if vertexs + vertext == G.vertex
    return true
  return false
end function
```

### correctness
the network G can be cut to two part with the mincut if and only if the two vertex collection 'S' and 'T' reachs combines the whole G.vertex

The Ford-Fulkerson complexity is \\(O(mC)\\), and the DFS to find the vertex needs \\(O(m)\\), so the complexity is \\(O(mn+2m)\\)


## Problem Reduction
There is a matrix with numbers which means the cost when you walk through this point. you are asked to walk through the matrix from the top left point to the right bottom point and then return to the top left point with the minimal cost. Note that when you walk from the top to the bottom you can just walk to the right or bottom point and when you return, you can just walk to the top or left point. And each point CAN NOT be walked through more than once.
