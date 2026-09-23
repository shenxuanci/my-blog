---
title: "滑动窗口"
date: "2026-09-22 00:00:00"
permalink: "/2026/09/22/hua-dong-chuang-kou/"
updated: "2026-09-22"
categories:
  - "数据结构与算法"
index_img: "/images/covers/defaults/data-structures-algorithms.webp"
---
```py
# 滑动窗口算法伪码框架
def slidingWindow(s: str):
    # 用合适的数据结构记录窗口中的数据，根据具体场景变通
    # 比如说，我想记录窗口中元素出现的次数，就用 map
    # 如果我想记录窗口中的元素和，就可以只用一个 int
    window = ...

    left, right = 0, 0
    while right < len(s):
        # c 是将移入窗口的字符
        c = s[right]
        window.add(c)
        # 增大窗口
        right += 1
        # 进行窗口内数据的一系列更新
        ...

        # *** debug 输出的位置 ***
        # 注意在最终的解法代码中不要 print
        # 因为 IO 操作很耗时，可能导致超时
        # print(f"window: [{left}, {right})")
        # ***********************

        # 判断左侧窗口是否要收缩
        while left < right and window needs shrink:
            # d 是将移出窗口的字符
            d = s[left]
            window.remove(d)
            # 缩小窗口
            left += 1
            # 进行窗口内数据的一系列更新
            ...
```

框架中两处`...`表示的是更新窗口数据的地方，做题时直接往这里面填代码逻辑即可。

## 这 12 道题覆盖什么

| 模型 | 代表题 | 你要形成的条件反射 |
|---|---|---|
| 定长窗口 | 438、2461 | 固定长度，右进左出，增量维护状态 |
| 求最长 | 3、424 | 非法时缩左，合法时更新最大长度 |
| 求最短 | 209、76 | 先扩到合法，再尽量缩短 |
| 计数：越短越合法 | 713 | `ans += right - left + 1` |
| 计数：越长越合法 | 1358 | 收缩到刚非法后 `ans += left` |
| 恰好型 | 930、992 | `exactly(K) = atMost(K) - atMost(K-1)` |
| 问题转化 | 1658 | 两端删除 → 中间最长子数组 |
| 窗口外条件 | 1234 | 窗口表示“准备替换的部分”，维护 outside |

# 438. 找到字符串中所有字母异位词

原题：https://leetcode.cn/problems/find-all-anagrams-in-a-string/

## 题目描述

给定两个字符串 `s` 和 `p`，找出 `s` 中所有与 `p` 互为字母异位词的连续子串，并返回这些子串的起始下标。

### 关键限制

- 子串长度必须等于 `len(p)`。
- 判断异位词只需要比较每个字符的出现次数。
- 若 `len(p) > len(s)`，答案为空。

### 必要示例

```text
输入：s = "cbaebabacd", p = "abc"
输出：[0, 6]
```

## 解法一：定长滑动窗口 + 频率数组

### 思路

窗口长度固定为 `len(p)`。右端加入新字符，窗口超过长度后移除最左字符。每次窗口长度正确时比较窗口频率与 `p` 的频率。

由于字符集只有 26 个小写字母，比较两个长度为 26 的数组仍可视为常数时间。

### Python 代码

```python
from typing import List


class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        n, m = len(s), len(p)
        if m > n:
            return []

        need = [0] * 26
        window = [0] * 26

        for ch in p:
            need[ord(ch) - ord('a')] += 1

        ans = []

        for right, ch in enumerate(s):
            window[ord(ch) - ord('a')] += 1

            if right >= m:
                left_ch = s[right - m]
                window[ord(left_ch) - ord('a')] -= 1

            if right >= m - 1 and window == need:
                ans.append(right - m + 1)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`，字符集大小固定为 26。
- 空间复杂度：`O(1)`。

## 解法二：差分数组 + 不同位置计数

### 思路

维护：

```text
diff[c] = 当前窗口中 c 的次数 - p 中 c 的次数
```

再维护 `different`，表示有多少个字符满足 `diff[c] != 0`。

窗口每次只进入和离开一个字符，因此只需更新两个位置，不必重新比较整个频率数组。当 `different == 0` 时，窗口就是异位词。

### Python 代码

```python
from typing import List


class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        n, m = len(s), len(p)
        if m > n:
            return []

        diff = [0] * 26

        for ch in p:
            diff[ord(ch) - ord('a')] -= 1

        for ch in s[:m]:
            diff[ord(ch) - ord('a')] += 1

        different = sum(value != 0 for value in diff)
        ans = []

        if different == 0:
            ans.append(0)

        def change(index: int, delta: int) -> None:
            nonlocal different

            before = diff[index]
            after = before + delta

            if before == 0 and after != 0:
                different += 1
            elif before != 0 and after == 0:
                different -= 1

            diff[index] = after

        for right in range(m, n):
            out_index = ord(s[right - m]) - ord('a')
            in_index = ord(s[right]) - ord('a')

            change(out_index, -1)
            change(in_index, 1)

            if different == 0:
                ans.append(right - m + 1)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

---

# 2461. 长度为 K 子数组中的最大和

原题：https://leetcode.cn/problems/maximum-sum-of-distinct-subarrays-with-length-k/

## 题目描述

给定整数数组 `nums` 和整数 `k`，要求找到长度恰好为 `k`、且所有元素互不相同的子数组中的最大元素和。如果不存在满足条件的子数组，返回 `0`。

### 关键限制

- 必须是连续子数组。
- 长度必须恰好为 `k`。
- 窗口内所有元素必须互不相同。

### 必要示例

```text
输入：nums = [1,5,4,2,9,9,9], k = 3
输出：15
```

## 解法一：定长滑动窗口 + 哈希计数 + 窗口和

### 思路

始终维护长度不超过 `k` 的窗口，同时维护：

- `window_sum`：窗口元素和；
- `count`：每个数字在窗口中的出现次数。

当窗口长度为 `k` 且 `len(count) == k` 时，说明 `k` 个元素全部不同，可以更新答案。

### Python 代码

```python
from collections import defaultdict
from typing import List


class Solution:
    def maximumSubarraySum(self, nums: List[int], k: int) -> int:
        count = defaultdict(int)
        window_sum = 0
        left = 0
        ans = 0

        for right, num in enumerate(nums):
            count[num] += 1
            window_sum += num

            if right - left + 1 > k:
                out = nums[left]
                count[out] -= 1
                window_sum -= out

                if count[out] == 0:
                    del count[out]

                left += 1

            if right - left + 1 == k and len(count) == k:
                ans = max(ans, window_sum)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(k)`。

## 解法二：最近出现位置 + 前缀和

### 思路

用 `left` 表示：以当前 `right` 为右端点时，保持元素互不相同所允许的最左边界。

若当前元素之前在窗口中出现过，就直接把 `left` 跳到它上次出现位置的后一位。

对于长度为 `k` 的候选窗口 `[right-k+1, right]`，只要：

```text
right - k + 1 >= left
```

就说明这个长度为 `k` 的窗口没有重复元素。窗口和通过前缀和 `O(1)` 得到。

### Python 代码

```python
from typing import List


class Solution:
    def maximumSubarraySum(self, nums: List[int], k: int) -> int:
        n = len(nums)
        prefix = [0] * (n + 1)
        last = {}

        left = 0
        ans = 0

        for right, num in enumerate(nums):
            prefix[right + 1] = prefix[right] + num

            if num in last and last[num] >= left:
                left = last[num] + 1

            last[num] = right

            start = right - k + 1

            if start >= left:
                current_sum = prefix[right + 1] - prefix[start]
                ans = max(ans, current_sum)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(n)`。

---

# 3. 无重复字符的最长子串

原题：https://leetcode.cn/problems/longest-substring-without-repeating-characters/

## 题目描述

给定字符串 `s`，求不含重复字符的最长连续子串的长度。

### 关键限制

- 必须是连续子串。
- 窗口中不能出现重复字符。

### 必要示例

```text
输入：s = "abcabcbb"
输出：3
```

## 解法一：集合 + 可变长度滑动窗口

### 思路

右指针不断扩张。当 `s[right]` 已经在窗口中时，不断移动左指针并从集合删除字符，直到当前字符可以安全加入。

窗口始终满足“所有字符互不重复”。

### Python 代码

```python
class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        window = set()
        left = 0
        ans = 0

        for right, ch in enumerate(s):
            while ch in window:
                window.remove(s[left])
                left += 1

            window.add(ch)
            ans = max(ans, right - left + 1)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`，每个字符最多进入和离开窗口一次。
- 空间复杂度：`O(Σ)`，`Σ` 为字符集大小；一般也可写作 `O(n)` 上界。

## 解法二：记录最近出现位置，左指针直接跳跃

### 思路

与其一个字符一个字符地缩小窗口，不如记录每个字符最近出现的下标。

若当前字符上次出现在当前窗口内，则可以直接：

```text
left = 上次出现位置 + 1
```

从而一次跳过整个无效区间。

### Python 代码

```python
class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        last = {}
        left = 0
        ans = 0

        for right, ch in enumerate(s):
            if ch in last and last[ch] >= left:
                left = last[ch] + 1

            last[ch] = right
            ans = max(ans, right - left + 1)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(Σ)`。

---

# 424. 替换后的最长重复字符

原题：https://leetcode.cn/problems/longest-repeating-character-replacement/

## 题目描述

给定只包含大写英文字母的字符串 `s` 和整数 `k`。你最多可以修改 `k` 个字符，求能够得到的最长、全部由同一字符组成的连续子串长度。

### 关键限制

一个窗口长度为 `L`，其中出现次数最多的字符出现 `max_freq` 次，则需要替换：

```text
L - max_freq
```

个字符。

窗口合法条件为：

```text
L - max_freq <= k
```

### 必要示例

```text
输入：s = "AABABBA", k = 1
输出：4
```

## 解法一：滑动窗口 + 最大字符频率

### 思路

不断扩大右端点，维护窗口内字符频率以及历史最大频率 `max_freq`。

当：

```text
窗口长度 - max_freq > k
```

时，窗口无法通过至多 `k` 次替换变成同一字符，需要移动左指针。

### Python 代码

```python
from collections import defaultdict


class Solution:
    def characterReplacement(self, s: str, k: int) -> int:
        count = defaultdict(int)
        left = 0
        max_freq = 0
        ans = 0

        for right, ch in enumerate(s):
            count[ch] += 1
            max_freq = max(max_freq, count[ch])

            while right - left + 1 - max_freq > k:
                count[s[left]] -= 1
                left += 1

            ans = max(ans, right - left + 1)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`，字符只有 26 种。

## 解法二：二分答案 + 定长窗口判定

### 思路

如果存在一个长度为 `L` 的合法窗口，那么更短的长度也一定可以做到，因此答案具有单调性，可以二分窗口长度。

对于固定长度 `L`，扫描所有长度为 `L` 的窗口。若某个窗口满足：

```text
L - 窗口最大字符频率 <= k
```

则长度 `L` 可行。

### Python 代码

```python
class Solution:
    def characterReplacement(self, s: str, k: int) -> int:
        n = len(s)

        def can(length: int) -> bool:
            count = [0] * 26

            for i, ch in enumerate(s):
                count[ord(ch) - ord('A')] += 1

                if i >= length:
                    out = s[i - length]
                    count[ord(out) - ord('A')] -= 1

                if i >= length - 1:
                    if length - max(count) <= k:
                        return True

            return False

        left, right = 0, n

        while left < right:
            mid = (left + right + 1) // 2

            if can(mid):
                left = mid
            else:
                right = mid - 1

        return left
```

### 复杂度分析

- 时间复杂度：`O(n log n)`，每次判定扫描一遍字符串。
- 空间复杂度：`O(1)`。

---

# 209. 长度最小的子数组

原题：https://leetcode.cn/problems/minimum-size-subarray-sum/

## 题目描述

给定一个正整数数组 `nums` 和正整数 `target`，找出元素和大于等于 `target` 的最短连续子数组长度。如果不存在，返回 `0`。

### 关键限制

- `nums` 中元素均为正数。
- 正数保证：右端扩张时和只会增大，左端收缩时和只会减小，这是滑动窗口成立的关键。

### 必要示例

```text
输入：target = 7, nums = [2,3,1,2,4,3]
输出：2
```

## 解法一：滑动窗口

### 思路

右指针扩张并累加窗口和。当窗口和达到 `target` 后，不断收缩左端，尽可能得到更短的合法窗口。

### Python 代码

```python
from typing import List


class Solution:
    def minSubArrayLen(self, target: int, nums: List[int]) -> int:
        left = 0
        window_sum = 0
        ans = len(nums) + 1

        for right, num in enumerate(nums):
            window_sum += num

            while window_sum >= target:
                ans = min(ans, right - left + 1)
                window_sum -= nums[left]
                left += 1

        return 0 if ans == len(nums) + 1 else ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

## 解法二：前缀和 + 二分查找

### 思路

因为数组元素全为正数，所以前缀和严格递增。

对于每个左边界 `i`，需要找到最小的 `j`，使：

```text
prefix[j] - prefix[i] >= target
```

等价于：

```text
prefix[j] >= prefix[i] + target
```

可以对前缀和数组二分查找。

### Python 代码

```python
from bisect import bisect_left
from typing import List


class Solution:
    def minSubArrayLen(self, target: int, nums: List[int]) -> int:
        n = len(nums)
        prefix = [0]

        for num in nums:
            prefix.append(prefix[-1] + num)

        ans = n + 1

        for i in range(n):
            need = prefix[i] + target
            j = bisect_left(prefix, need, i + 1)

            if j <= n:
                ans = min(ans, j - i)

        return 0 if ans == n + 1 else ans
```

### 复杂度分析

- 时间复杂度：`O(n log n)`。
- 空间复杂度：`O(n)`。

---

# 76. 最小覆盖子串

原题：https://leetcode.cn/problems/minimum-window-substring/

## 题目描述

给定字符串 `s` 和 `t`，在 `s` 中寻找最短连续子串，使该子串包含 `t` 中全部字符，并且每个字符的出现次数也至少达到 `t` 中的要求。若不存在，返回空字符串。

### 关键限制

- 不只是包含字符种类，还必须满足字符出现次数。
- 目标是“满足覆盖条件的最短窗口”。

### 必要示例

```text
输入：s = "ADOBECODEBANC", t = "ABC"
输出："BANC"
```

## 解法一：缺口计数滑动窗口

### 思路

`need[c]` 表示当前窗口还缺多少个字符 `c`。

`missing` 表示总共还缺多少个字符。当 `missing == 0` 时，窗口已经覆盖 `t`，此时不断移动左指针寻找最短窗口。

### Python 代码

```python
from collections import Counter


class Solution:
    def minWindow(self, s: str, t: str) -> str:
        if not s or not t:
            return ""

        need = Counter(t)
        missing = len(t)
        left = 0

        best_len = float('inf')
        best_left = 0
        best_right = 0

        for right, ch in enumerate(s):
            if need[ch] > 0:
                missing -= 1

            need[ch] -= 1

            while missing == 0:
                if right - left + 1 < best_len:
                    best_len = right - left + 1
                    best_left = left
                    best_right = right + 1

                out = s[left]
                need[out] += 1

                if need[out] > 0:
                    missing += 1

                left += 1

        if best_len == float('inf'):
            return ""

        return s[best_left:best_right]
```

### 复杂度分析

- 时间复杂度：`O(|s| + |t|)`。
- 空间复杂度：`O(Σ)`。

## 解法二：过滤无关字符后的滑动窗口

### 思路

如果 `t` 中字符很少，而 `s` 很长，则 `s` 中大量字符根本不会影响窗口是否合法。

先只保留 `s` 中属于 `t` 的字符及其原下标，然后只在这些有效位置上滑动窗口，可以减少实际扫描和频率更新次数。

### Python 代码

```python
from collections import Counter, defaultdict


class Solution:
    def minWindow(self, s: str, t: str) -> str:
        if not s or not t:
            return ""

        need = Counter(t)
        required = len(need)

        filtered = [
            (i, ch)
            for i, ch in enumerate(s)
            if ch in need
        ]

        window = defaultdict(int)
        formed = 0
        left = 0

        best_len = float('inf')
        best_left = 0
        best_right = 0

        for right in range(len(filtered)):
            index, ch = filtered[right]
            window[ch] += 1

            if window[ch] == need[ch]:
                formed += 1

            while formed == required and left <= right:
                start = filtered[left][0]
                end = index

                if end - start + 1 < best_len:
                    best_len = end - start + 1
                    best_left = start
                    best_right = end + 1

                left_ch = filtered[left][1]
                window[left_ch] -= 1

                if window[left_ch] < need[left_ch]:
                    formed -= 1

                left += 1

        if best_len == float('inf'):
            return ""

        return s[best_left:best_right]
```

### 复杂度分析

- 时间复杂度：`O(|s| + |t|)`。
- 空间复杂度：`O(|s| + Σ)`，最坏情况下过滤数组包含整个 `s`。

---

# 713. 乘积小于 K 的子数组

原题：https://leetcode.cn/problems/subarray-product-less-than-k/

## 题目描述

给定正整数数组 `nums` 和整数 `k`，统计乘积严格小于 `k` 的连续子数组数量。

### 关键限制

- `nums` 中元素均为正数。
- 条件是严格小于 `k`。
- 若 `k <= 1`，由于元素均为正整数，不存在合法非空子数组。

### 必要示例

```text
输入：nums = [10,5,2,6], k = 100
输出：8
```

## 解法一：滑动窗口 + `right - left + 1` 计数

### 思路

维护窗口乘积小于 `k`。

当右端点固定为 `right` 时，只要 `[left, right]` 合法，那么：

```text
[left, right]
[left+1, right]
...
[right, right]
```

全部合法，因此新增子数组数量为：

```text
right - left + 1
```

### Python 代码

```python
from typing import List


class Solution:
    def numSubarrayProductLessThanK(self, nums: List[int], k: int) -> int:
        if k <= 1:
            return 0

        product = 1
        left = 0
        ans = 0

        for right, num in enumerate(nums):
            product *= num

            while product >= k:
                product //= nums[left]
                left += 1

            ans += right - left + 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

## 解法二：对数前缀和 + 二分查找（次优但值得掌握）

### 思路

因为：

```text
log(a × b) = log(a) + log(b)
```

所以子数组乘积条件：

```text
product < k
```

可以转化为：

```text
prefix_log[j] - prefix_log[i] < log(k)
```

由于 `nums` 都为正整数，`log(nums[i]) >= 0`，前缀对数数组单调不减，可以为每个左端点二分右边界。

该方法主要用于理解“乘法约束 → 加法约束 → 二分”的转化；实际刷题更推荐滑动窗口。浮点数计算时需要留出误差量。

### Python 代码

```python
from bisect import bisect_left
from math import log
from typing import List


class Solution:
    def numSubarrayProductLessThanK(self, nums: List[int], k: int) -> int:
        if k <= 1:
            return 0

        n = len(nums)
        prefix = [0.0] * (n + 1)

        for i, num in enumerate(nums):
            prefix[i + 1] = prefix[i] + log(num)

        limit = log(k)
        eps = 1e-12
        ans = 0

        for left in range(n):
            target = prefix[left] + limit

            # 找到第一个不再满足 prefix[right] < target 的位置。
            first_invalid = bisect_left(
                prefix,
                target - eps,
                left + 1,
                n + 1,
            )

            ans += first_invalid - left - 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n log n)`。
- 空间复杂度：`O(n)`。

---

# 1358. 包含所有三种字符的子字符串数目

原题：https://leetcode.cn/problems/number-of-substrings-containing-all-three-characters/

## 题目描述

给定只由 `'a'`、`'b'`、`'c'` 组成的字符串 `s`，统计同时至少包含一个 `'a'`、一个 `'b'`、一个 `'c'` 的连续子字符串数量。

### 关键限制

- 字符串只包含 `a / b / c`。
- 只要一个窗口已经包含三种字符，再向左扩展仍然合法。

### 必要示例

```text
输入：s = "abcabc"
输出：10
```

## 解法一：滑动窗口 + `ans += left`

### 思路

对每个右端点，先扩大窗口，然后只要窗口同时包含 `a / b / c`，就持续收缩左端点。

收缩结束后，`left` 恰好表示：

```text
以 right 为右端点时，一共有 left 个合法起点
```

因此：

```text
ans += left
```

### Python 代码

```python
class Solution:
    def numberOfSubstrings(self, s: str) -> int:
        count = [0, 0, 0]
        left = 0
        ans = 0

        for ch in s:
            count[ord(ch) - ord('a')] += 1

            while min(count) > 0:
                count[ord(s[left]) - ord('a')] -= 1
                left += 1

            ans += left

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

## 解法二：记录三种字符最后出现位置

### 思路

设当前扫描到位置 `i`，记录：

```text
last[a], last[b], last[c]
```

如果三种字符都已经出现，那么一个以 `i` 为右端点的子串想同时包含三种字符，其左端点最大只能到三者最后出现位置中的最小值。

因此新增合法子串数量为：

```text
min(last) + 1
```

### Python 代码

```python
class Solution:
    def numberOfSubstrings(self, s: str) -> int:
        last = [-1, -1, -1]
        ans = 0

        for i, ch in enumerate(s):
            last[ord(ch) - ord('a')] = i

            earliest = min(last)

            if earliest != -1:
                ans += earliest + 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

---

# 930. 和相同的二元子数组

原题：https://leetcode.cn/problems/binary-subarrays-with-sum/

## 题目描述

给定只包含 `0` 和 `1` 的数组 `nums` 以及整数 `goal`，统计元素和恰好等于 `goal` 的连续子数组数量。

### 关键限制

- 数组是二元数组，因此所有元素非负。
- “恰好等于”可以转化为两个“至多”问题之差。

### 必要示例

```text
输入：nums = [1,0,1,0,1], goal = 2
输出：4
```

## 解法一：前缀和 + 哈希计数

### 思路

若：

```text
prefix[j] - prefix[i] = goal
```

则：

```text
prefix[i] = prefix[j] - goal
```

扫描数组时，统计之前出现过多少个 `prefix - goal` 即可。

### Python 代码

```python
from collections import defaultdict
from typing import List


class Solution:
    def numSubarraysWithSum(self, nums: List[int], goal: int) -> int:
        count = defaultdict(int)
        count[0] = 1

        prefix = 0
        ans = 0

        for num in nums:
            prefix += num
            ans += count[prefix - goal]
            count[prefix] += 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(n)`。

## 解法二：恰好 = 至多(goal) - 至多(goal - 1)

### 思路

定义：

```text
atMost(k) = 和 <= k 的子数组数量
```

因为数组元素非负，可以用滑动窗口计算 `atMost(k)`。

那么：

```text
和恰好等于 goal
= 和 <= goal
- 和 <= goal - 1
```

### Python 代码

```python
from typing import List


class Solution:
    def numSubarraysWithSum(self, nums: List[int], goal: int) -> int:
        def atMost(limit: int) -> int:
            if limit < 0:
                return 0

            left = 0
            window_sum = 0
            count = 0

            for right, num in enumerate(nums):
                window_sum += num

                while window_sum > limit:
                    window_sum -= nums[left]
                    left += 1

                count += right - left + 1

            return count

        return atMost(goal) - atMost(goal - 1)
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

---

# 992. K 个不同整数的子数组

原题：https://leetcode.cn/problems/subarrays-with-k-different-integers/

## 题目描述

给定整数数组 `nums` 和整数 `k`，统计恰好包含 `k` 个不同整数的连续子数组数量。

### 关键限制

- 求的是不同整数的种类数，不是元素个数。
- “恰好 K 种”直接维护不方便，但“至多 K 种”天然适合滑动窗口。

### 必要示例

```text
输入：nums = [1,2,1,2,3], k = 2
输出：7
```

## 解法一：`atMost(k) - atMost(k - 1)`

### 思路

定义：

```text
atMost(k) = 至多包含 k 种不同整数的子数组数量
```

那么：

```text
恰好 k 种
= 至多 k 种
- 至多 k - 1 种
```

`atMost` 内部使用标准可变长度滑动窗口。

### Python 代码

```python
from collections import defaultdict
from typing import List


class Solution:
    def subarraysWithKDistinct(self, nums: List[int], k: int) -> int:
        def atMost(limit: int) -> int:
            count = defaultdict(int)
            left = 0
            distinct = 0
            ans = 0

            for right, num in enumerate(nums):
                if count[num] == 0:
                    distinct += 1

                count[num] += 1

                while distinct > limit:
                    out = nums[left]
                    count[out] -= 1

                    if count[out] == 0:
                        distinct -= 1

                    left += 1

                ans += right - left + 1

            return ans

        return atMost(k) - atMost(k - 1)
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(k)` 到 `O(n)`，取决于窗口中不同元素数量。

## 解法二：双滑动窗口单遍统计

### 思路

同时维护两个窗口：

- 窗口 1：至多包含 `k` 种不同整数，左端点为 `left_k`；
- 窗口 2：至多包含 `k-1` 种不同整数，左端点为 `left_k_minus_1`。

对于同一个右端点：

```text
left_k ... left_k_minus_1 - 1
```

这些起点对应的子数组都恰好包含 `k` 种不同整数，因此新增数量为：

```text
left_k_minus_1 - left_k
```

### Python 代码

```python
from collections import defaultdict
from typing import List


class Solution:
    def subarraysWithKDistinct(self, nums: List[int], k: int) -> int:
        count_k = defaultdict(int)
        count_k_minus_1 = defaultdict(int)

        left_k = 0
        left_k_minus_1 = 0
        distinct_k = 0
        distinct_k_minus_1 = 0
        ans = 0

        for right, num in enumerate(nums):
            if count_k[num] == 0:
                distinct_k += 1
            count_k[num] += 1

            if count_k_minus_1[num] == 0:
                distinct_k_minus_1 += 1
            count_k_minus_1[num] += 1

            while distinct_k > k:
                out = nums[left_k]
                count_k[out] -= 1

                if count_k[out] == 0:
                    distinct_k -= 1

                left_k += 1

            while distinct_k_minus_1 > k - 1:
                out = nums[left_k_minus_1]
                count_k_minus_1[out] -= 1

                if count_k_minus_1[out] == 0:
                    distinct_k_minus_1 -= 1

                left_k_minus_1 += 1

            ans += left_k_minus_1 - left_k

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(n)` 最坏情况。

---

# 1658. 将 x 减到 0 的最小操作数

原题：https://leetcode.cn/problems/minimum-operations-to-reduce-x-to-zero/

## 题目描述

给定正整数数组 `nums` 和整数 `x`。每次只能删除数组最左端或最右端的一个元素，并从 `x` 中减去该元素。要求把 `x` 恰好减到 `0`，返回最少操作次数；无法做到时返回 `-1`。

### 关键限制

删除两端若干元素后，剩下的一定是原数组中的一个连续子数组。

因此：

```text
删除元素和 = x
```

等价于：

```text
保留的中间子数组和 = sum(nums) - x
```

最小化删除数量，就是最大化保留子数组长度。

### 必要示例

```text
输入：nums = [1,1,4,2,3], x = 5
输出：2
```

## 解法一：转化为最长定和子数组 + 滑动窗口

### 思路

令：

```text
target = sum(nums) - x
```

因为 `nums` 全是正数，可以用滑动窗口找到和恰好等于 `target` 的最长子数组。

若最长保留长度为 `best`，答案就是：

```text
n - best
```

### Python 代码

```python
from typing import List


class Solution:
    def minOperations(self, nums: List[int], x: int) -> int:
        target = sum(nums) - x

        if target < 0:
            return -1

        left = 0
        window_sum = 0
        best = -1

        for right, num in enumerate(nums):
            window_sum += num

            while window_sum > target and left <= right:
                window_sum -= nums[left]
                left += 1

            if window_sum == target:
                best = max(best, right - left + 1)

        return -1 if best == -1 else len(nums) - best
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

## 解法二：前缀和 + 哈希表求最长定和子数组

### 思路

仍然先转化为寻找和为 `target` 的最长连续子数组。

若当前前缀和为 `prefix`，那么需要查找之前是否存在：

```text
prefix - target
```

为了让子数组尽可能长，只记录某个前缀和第一次出现的位置。

### Python 代码

```python
from typing import List


class Solution:
    def minOperations(self, nums: List[int], x: int) -> int:
        target = sum(nums) - x

        if target < 0:
            return -1

        first = {0: -1}
        prefix = 0
        best = -1

        for i, num in enumerate(nums):
            prefix += num

            need = prefix - target
            if need in first:
                best = max(best, i - first[need])

            if prefix not in first:
                first[prefix] = i

        return -1 if best == -1 else len(nums) - best
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(n)`。

---

# 1234. 替换子串得到平衡字符串

原题：https://leetcode.cn/problems/replace-the-substring-for-balanced-string/

## 题目描述

给定一个只包含 `Q / W / E / R` 的字符串 `s`，长度为 `n`。若四种字符都恰好出现 `n / 4` 次，则字符串平衡。

你可以选择一个连续子串，并把它替换成任意相同长度的字符串。求为了使整个字符串平衡，最短需要替换多长的子串。

### 关键限制

真正需要满足的不是“窗口里面长什么样”，而是：

> 把某个窗口拿出去准备替换后，窗口外每种字符的数量都不能超过 `n / 4`。

只要窗口外已经满足这个条件，窗口内部就一定可以通过重新填写来补齐缺失字符。

### 必要示例

```text
输入：s = "QQWE"
输出：1
```

## 解法一：维护窗口外计数的滑动窗口

### 思路

先统计整个字符串的字符数量。

右指针把字符纳入“待替换窗口”时，就从外部计数中减掉该字符。

若窗口外四种字符都不超过 `n / 4`，说明当前窗口已经足够大，可以尝试移动左指针缩短窗口。

### Python 代码

```python
from collections import Counter


class Solution:
    def balancedString(self, s: str) -> int:
        n = len(s)
        target = n // 4
        outside = Counter(s)

        if all(outside[ch] == target for ch in "QWER"):
            return 0

        left = 0
        ans = n

        for right, ch in enumerate(s):
            outside[ch] -= 1

            while all(outside[c] <= target for c in "QWER"):
                ans = min(ans, right - left + 1)
                outside[s[left]] += 1
                left += 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`。
- 空间复杂度：`O(1)`。

## 解法二：二分答案 + 固定长度窗口判定

### 思路

如果长度为 `L` 的某个窗口可以被替换后使字符串平衡，那么更长的窗口也一定可以做到，因此“可行窗口长度”具有单调性。

可以二分最小长度 `L`。对于每个固定长度窗口，计算窗口外的 `Q / W / E / R` 数量，判断是否全部不超过 `n / 4`。

### Python 代码

```python
from collections import Counter


class Solution:
    def balancedString(self, s: str) -> int:
        n = len(s)
        target = n // 4
        chars = "QWER"

        total = Counter(s)

        if all(total[ch] == target for ch in chars):
            return 0

        index = {ch: i for i, ch in enumerate(chars)}
        prefix = [[0] * (n + 1) for _ in range(4)]

        for i, ch in enumerate(s):
            for c in range(4):
                prefix[c][i + 1] = prefix[c][i]
            prefix[index[ch]][i + 1] += 1

        def can(length: int) -> bool:
            for left in range(n - length + 1):
                right = left + length
                valid = True

                for c, ch in enumerate(chars):
                    inside = prefix[c][right] - prefix[c][left]
                    outside = total[ch] - inside

                    if outside > target:
                        valid = False
                        break

                if valid:
                    return True

            return False

        left, right = 0, n

        while left < right:
            mid = (left + right) // 2

            if can(mid):
                right = mid
            else:
                left = mid + 1

        return left
```

### 复杂度分析

- 时间复杂度：`O(n log n)`。
- 空间复杂度：`O(n)`。

# 专题总结：滑动窗口到底在维护什么

## 1. 先判断是不是滑动窗口

滑动窗口通常适合满足以下特征的问题：

1. 研究对象是**连续子数组 / 连续子串**。
2. 左右边界只需要向右移动，不需要回退。
3. 当窗口不满足条件时，可以通过移动某一端恢复合法性。
4. 窗口状态可以随着“加入一个元素 / 删除一个元素”增量维护。

真正关键的是**单调性**。例如正数数组中的和、正整数数组中的乘积、不同元素种数、字符频率等，都常常具有适合双指针移动的单调结构。

## 2. 定长窗口模板

```python
left = 0

for right, x in enumerate(nums):
    # 1. x 进入窗口
    add(x)

    # 2. 超过固定长度 k，就移出一个
    if right - left + 1 > k:
        remove(nums[left])
        left += 1

    # 3. 长度恰好为 k 时处理答案
    if right - left + 1 == k:
        update_answer()
```

对应代表题：**438、2461**。

## 3. 不定长：求最长模板

```python
left = 0

for right, x in enumerate(nums):
    add(x)

    while window_is_invalid():
        remove(nums[left])
        left += 1

    ans = max(ans, right - left + 1)
```

核心语义：**更新答案之前，窗口必须合法**。

对应代表题：**3、424**。

## 4. 不定长：求最短模板

```python
left = 0

for right, x in enumerate(nums):
    add(x)

    while window_is_valid():
        ans = min(ans, right - left + 1)
        remove(nums[left])
        left += 1
```

核心语义：**一旦合法就不断收缩，在收缩阶段寻找最短答案**。

对应代表题：**209、76**。

## 5. 计数型：越短越合法

当 `[left, right]` 合法，而且删除左侧元素后仍然合法，那么固定 `right` 后：

```text
[left, right]
[left+1, right]
...
[right, right]
```

都合法，所以：

```python
ans += right - left + 1
```

代表题：**713、930 的 atMost、992 的 atMost**。

## 6. 计数型：越长越合法

如果某窗口一旦满足条件，再向左扩展也一定满足，那么可以把窗口不断收缩到刚好失效。此时左边所有更早的起点都是合法起点。

代表题：**1358**。

## 7. 恰好型转换

这是本组题最值得长期记住的公式之一：

```text
恰好 K
= 至多 K
- 至多 K-1
```

它把难维护的“等于”条件，变成两个天然适合滑窗的单调条件。

代表题：**930、992**。

## 8. 做题时固定问自己的 6 个问题

1. **窗口 `[left, right]` 代表什么？**
2. **窗口里需要维护哪些状态？** 和、乘积、频率、不同种数、缺口，还是窗口外计数？
3. **什么条件下窗口合法 / 非法？**
4. **left 在什么时候移动？** 合法时缩，还是非法时缩？
5. **答案在什么时候更新？** 扩张后、收缩前、收缩过程中，还是收缩结束后？
6. **固定 right 后，能不能一次性统计一批左端点？**

只要这六个问题能回答清楚，绝大多数滑动窗口代码都只是把这些状态翻译成 Python。
