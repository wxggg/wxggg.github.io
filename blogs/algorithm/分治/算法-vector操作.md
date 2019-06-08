本文记录关于vector的一些算法题目。

### 1. stl提供的基本操作 
在stl模板中提供了lower_bound和upper_bound函数，lower_bound函数作为二分查找的底层实现非常有用。lower_bound返回的是第一个大于等于x的下标，upper_bound返回的是第一个大于x的下标，当返回n的时候说明最大的值也比x要大。

```c++
template <typename T>
int lower_bound(const vector<T> &vec, const T &value) {
    if (vec.empty()) return 0;
    int left = 0, right = vec.size() - 1, mid;
    if (vec[right] < value) return vec.size();
    while (vec[left] < value && left < right) {
        mid = (left + right) / 2;
        if (vec[mid] < value)
            left = mid + 1;
        else
            right = mid;
    }
    return left;
}
```

stl还提供一个分割函数partition，能够将vector分为两个部分，提供一个pred来提供一个判断条件，满足条件的值在左半边，不满足的在右边。

```c++
template <typename T, typename Predicate>
int partition(vector<T> &vec, int first, int last, Predicate pred) {
    --last;
    while (first < last) {
        while (first < last && pred(vec[first])) ++first;
        while (first < last && !pred(vec[last])) --last;
        std::swap(vec[first], vec[last]);
    }
    return first;
}
```

另外还提供一个nth_element(begin, nth, end)函数，能够通过调整让第n个元素刚好是第n大的。


### 2. 查询
首先lower_bound本身是具备二分查找的功能的，还存在其他类型的查找。如果是顺序数组查询的话都可以采用lower_bound进行二分查找。

例如查找target的左右下标：
```c++
vector<int> searchRange(vector<int> &nums, int target) {
    auto low = std::lower_bound(nums.begin(), nums.end(), target);
    if (low == nums.end() || *low != target) return {-1, -1};
    auto high = std::upper_bound(nums.begin(), nums.end(), target);
    return {low - nums.begin(), high - nums.begin() - 1};
}
```

对于leetcode上的题目：一个顺序数组绕某个元素被旋转了，也可以采用二分查找，但是不能直接使用lower_bound，二分判断的时候有一个非常重要的问题，首先就是如果只有两个数的话，mid和left是相等的，这里需要单独处理，可以直接将left++。另外如果数组存在重复元素的话，在找到的中间元素与left相等时，也就是不能够区分mid在左半边还是右半边的话，也可以直接将left++。存在重复元素可能会导致最坏复杂度为O(n)。
```c++
int search(vector<int> &nums, int target) {
    int left = 0, right = nums.size() - 1, mid;
    while (left <= right) {
        mid = (left + right) / 2;
        if (nums[mid] == target) return mid;
        if (nums[mid] > nums[left]) {
            if (nums[left] <= target && target < nums[mid])
                right = mid - 1;
            else
                left = mid + 1;
        } else if (nums[mid] < nums[left]) {
            if (nums[mid] < target && target <= nums[right])
                left = mid + 1;
            else
                right = mid - 1;
        } else
            left++;
    }
    return -1;
}
```

