CombinationSum问题是leetcode上面一类非常经典的回溯问题，这一类问题包括几个不同的变种。

## __[39. Combination Sum](https://leetcode.com/problems/combination-sum/)__

首先是从一组候选值中选取合适的组合combination，使得combination的和等于target，__注意个候选值可以被多次使用。__

回溯的思想其实就是选择一种可能，然后不断的深度搜索基于此种可能存在的解。这里从第一个candidate开始搜索，也就是从i=0开始搜索，在使用了candidates[i]之后，因为每个候选可以被多次使用，所以继续递归的时候i仍然是i。

只有当选择i的情况都搜索完了，递归返回的时候才进行下一个值的搜索。这里非常巧妙的是在使用candidates[i]之前将其push进入combination中，combination是当前可能存在的解，而在搜索了包含candidates[i]的结果之后就将其pop出来。

另外还需要注意的是，在开始回溯递归之前需要先将candidates排序，这里如果说明了candidates中的值不重复的话可以不用排序，但是在大多数情况下排序能避免重复解。

```c++
void backtrack(vector<vector<int>> &res, vector<int> &combination,
               vector<int> &candidates, int target, int i) {
    if (target == 0) {
        res.push_back(combination);
        return;
    }
    while (i < candidates.size() && candidates[i] <= target) {
        combination.push_back(candidates[i]);
        backtrack(res, combination, candidates, target - candidates[i], i);
        combination.pop_back();
        i++;
    }
}

vector<vector<int>> combinationSum(vector<int> &candidates, int target) {
    std::sort(candidates.begin(), candidates.end());
    vector<vector<int>> res;
    vector<int> combination;
    backtrack(res, combination, candidates, target, 0);
    return res;
}
```

## __[40. Combination Sum II](https://leetcode.com/problems/combination-sum-ii/)__

CombinationSum2的要求是candidates中会有重复的值，并且每个candidate都只能使用一次，这个要求就造成了上述解可能存在重复解，因为candidate中可能有重复的值。

这里也要先对candidate进排序，然后在递归之前先判断是否使用了相同的值递归，只有在使用不同值的时候才进行递归。

```c++
    int begin = i;
    while (i < candidates.size() && candidates[i] <= target) {
        combination.push_back(candidates[i]);
        if (i == begin || candidates[i] != candidates[i-1])
            backtrack(res, combination, candidates, target - candidates[i], i+1);
        combination.pop_back();
        i++;
    }
```

## __[216. Combination Sum III](https://leetcode.com/problems/combination-sum-iii/)__

CombininationSum3问题变成了从1到9中combination，并且combination中的值只能用一次，解法原理基本没变

```c++
void backtrack(vector<vector<int>> &res, vector<int> &combination, int k , int n, int i) {
    if (n == 0 && k==0) {
        res.push_back(combination); 
        return;
    }
    
    while(i < 10 && i <= n) {
        combination.push_back(i);
        backtrack(res, combination, k-1, n-i, i+1);
        combination.pop_back();
        i++;
    }
} 
```

## __[377. Combination Sum IV](https://leetcode.com/problems/combination-sum-iv/)__

CombinationSum4的题目为，从无重复的nums数组中选择combination，和为target的组合种数，这里数组中的值可以多次使用。这里目标结果是种数，所以应该在回溯的过程中使用动态规划来保存计算过的子结果。

```c++
int backtrack(vector<int> &nums,vector<int> &dp, int target) {
    if (dp[target]>=0) return dp[target];
    dp[target] = 0;
    for(int i=0; i<nums.size() && nums[i] <= target; i++) 
        dp[target] += backtrack(nums,dp, target - nums[i]);
    return dp[target];
}
```

## __[77. Combinations](https://leetcode.com/problems/combinations/)__

这题也是combination类型的题目，要求找出所有1到n中选择k个数的组合。

```c++
void backtrack(vector<vector<int>> &res, vector<int> &combination, int n, int k, int i) {
    if (k == 0) {
        res.push_back(combination);
        return;
    }
    while(i <= n) {
        combination.push_back(i);
        backtrack(res, combination, n, k-1, i+1);
        combination.pop_back();
        i++;
    }
}
```