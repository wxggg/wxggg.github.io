
## lower_bound
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

## partition

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

## nth_element
另外还提供一个nth_element(begin, nth, end)函数，能够通过调整让第n个元素刚好是第n大的, 如果是begin()+k的话，就应该是arr[k]元素。