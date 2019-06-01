## 1 Largest Divisible Subset
Given a set of distinct positive integers, find the largest subset such that every pair \\((Si, Sj)\\) of elements in this subset satisfies:Si%Sj = 0 or Sj%Si = 0.

### solution

the optimal structure is
$$ OPT(i) = max{OPT(other(i)+Si), OPT(i-1)}$$

other(i) demotes all the values that satisfy Si%v == 0, if Si is already in the OPT(i-1), then there is no need to do the repeated work.

```python
function subset(S)
    sub = []
    for i from 0 to len(S)
        v = S[i]
        if v in sub continue // already in opt
        for j from 0 to len(S)
            if j != i and satisfy(Sj,v)
                ss.append(S[j])
        subsub = subset(ss)
        if len(subsub)+1 > len(sub)
            sub = subsub + 1 // update opt
    end for
end function
```

### correctness
every value and its subset will be calculated, there is an optimal array, if the value tested is already in, there is no need to do repeated work

every value will be tested its subset, so the complexity is \\(O(n^2)\\)

## 2 Money robbing
A robber is planning to rob houses along a street. Each house has a certain amount of money stashed, the only constraint stopping you from robbing each of them is that adjacent houses have security system connected and it will automatically contact the police if two adjacent houses were broken into on the same night.

1. Given a list of non-negative integers representing the amount of money of each house, determine the maximum amount of money you can rob tonight without alerting the police
2. What if all houses are arranged in a circle?

### solution
the optimal structure is
$$ OPT(i) = max<value(i)+OPT(i-2), OPT(i-1)>$$

the value(i) denotes the money in room i, OPT(i) denotes the total rob money of the before i rooms

```python
function rob(i)
    if i==0 then
        return value[0]
    return max{value[i]+rob(i-2), rob(i-1)}
```
### correctness
if we rob room i, then we can only rob the before i-2 rooms, if not, then we can rob the before i-1 rooms, to compare the sum, we can always choose the most money to rob

the problem is \\(T(n) = T(n-1) + T(n-2) + C)\\), use array to store the past result, then the final time complexity is \\(O(n)\\)

### solution for circle
compare these two situations, and get the optimal solution
1. rob 1~n-1 rooms
2. rob 2~n rooms

## 3 Partition
Given a string s, partition s such that every substring of the partition is a palindrome. Return the minimum cuts needed for a palindrome partitioning of s.

For example, given \\(s = “aab”\\), return 1 since the palindrome partitioning \\([“aa”, “b”]\\) could be produced using 1 cut.

### solution
the optimal sub structure: \\(OPT(S)\\)
$$ OPT(S[left:right]+left+right) $$
$$ min<OPT(left(S))+right, OPT(right(S))+left>$$
$$ left $$

the left and right denotes the position of the longest palindrome from the left and right

1. so if left is smaller then right, then cut the 2 parts
2. if left is larger then right, can only cut one, so compare the two situations
3. if left == right, then 1 cut will satisfy

```python
function cut(S)
    //find the left and right longest palindrome
    if left == right then
        return left
    else if left < right then
        return left + right + cut(S[left:right])
    else
        return min{left + cut(S[:right]), right + cut(S[left:])}
end function
```

### correctness
every time we cut as many palindrome as possible, so this will make sure that the cuts will be least

__good situation:__ \
if the string is cut half and half, the problem is \\(T(n) = T(n/2) + cn\\), so the complexity is \\(O(n)\\)

__bad situation:__ \
if the string is cut 1 each time, the complexity will be \\(O(n^2)\\)


## 4 Decoding
A message containing letters from A-Z is being encoded to numbers using the following mapping:

    A : 1
    B : 2
    . . .
    Z : 26

Given an encoded message containing digits, determine the total number of ways to decode it.

For example, given encoded message “12”, it could be decoded as “AB” (1 2) or “L” (12). The number of ways decoding “12” is 2.

### solution
the optimal structure is: \
if N[i-1]=1, N[i-1]=2 and N[i] is 0~6
$$ OPT(i) = OPT(i-2) + OPT(i-1) $$
if N[i-1]=2 and N[i] is 7~9,  N[i-1] is 0,3~9
$$ OPT(i) = OPT(i-1) $$

the OPT(i) denotes the decoding numbers of the i prior numbers

### correctness
if i==1, return 1 \
if i==2, two situation, if S[1] and S[2] can be combined, or not \
if i=1 to n-1 is correct, then when i==n, it can be represented as problem i-1 and i-2, so it is correct

to traverse the array for 1 time, we can get the result, so \\(T(n) = T(n-2) + T(n-1)\\), so the complexity is \\(O(n)\\)

## 5 Longest Consecutive Subsequence
You are given a sequence L and an integer k, your task is to find the longest consecutive subsequence the sum of which is the multiple of k.

### solution
the optimal structure is: \
lengthk denotes the length of sequence that satisfy condition and contain the k value \
OPT(i) denotes the prior i values optimal solution, so:
$$ OPT(i) = max<lengthk, OPT(i-1)> $$

```python
function subsequence(L,i,k)
    if i == 0 return 0
    subsequence = //find the subsequce included L[i] and satisfy condition
    lengthk = len(subsequence)
    return max{subsequence(L,i-1,k), lengthk}
end function
```

### correctness
every time to work on the L[i] we choose the bigger result between OPT(i-1) and the result with L[i], so we always get the longest array

every value will be visited, and have to search the prior values to get a condition-satisfied subsequence, so the complexity is \\(O(n^2)\\)
