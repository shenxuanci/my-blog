---
title: "双指针"
date: "2026-09-22 00:00:00"
permalink: "/2026/09/22/shuang-zhi-zhen/"
updated: "2026-09-22"
categories:
  - "数据结构与算法"
index_img: "/images/covers/defaults/data-structures-algorithms.webp"
---
双指针本质上是一种**通过两个位置变量减少重复枚举**的思想。

```text
双指针
├─ 同向快慢指针
│  ├─ fast：读取 / 探索
│  └─ slow：写入 / 维护有效区
│
├─ 相向双指针
│  ├─ left 从左往右
│  └─ right 从右往左
│     依靠有序性 / 单调性排除候选
│
├─ 相背双指针
│  └─ 从中心向两侧扩张，例如回文
│
├─ 双端模拟
│  └─ 两个角色从两端同步推进
│
└─ 快慢指针判环
   ├─ slow 每次一步
   └─ fast 每次两步
```


# 283. 移动零

题目链接：https://leetcode.cn/problems/move-zeroes/

## 题目描述

给定整数数组 `nums`，要求把数组中的所有 `0` 移动到末尾，同时保持所有非零元素原来的相对顺序。

必须直接修改原数组，不需要返回新的数组。

### 关键限制

- 非零元素之间的相对顺序不能改变。
- 目标解法应原地完成。

### 必要示例

```text
输入：nums = [0,1,0,3,12]
修改后：[1,3,12,0,0]
```

## 解法一：快慢指针交换（最优）

### 思路

`fast` 扫描整个数组，`slow` 指向“下一个应该放非零元素的位置”。

遇到非零元素时，把 `nums[fast]` 和 `nums[slow]` 交换，再让 `slow += 1`。

这样每个非零元素都会被稳定地搬到前面，剩余位置自然都是零。

### Python 代码

```python
from typing import List


class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        slow = 0

        for fast in range(len(nums)):
            if nums[fast] != 0:
                nums[slow], nums[fast] = nums[fast], nums[slow]
                slow += 1
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：提取非零元素后回写（次优但直观）

### 思路

先收集所有非零元素，再覆盖原数组前半部分，最后把剩余位置填成 `0`。

代码很直观，但需要额外数组，所以空间复杂度不如双指针。

### Python 代码

```python
from typing import List


class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        non_zero = [x for x in nums if x != 0]
        k = len(non_zero)

        nums[:k] = non_zero
        nums[k:] = [0] * (len(nums) - k)
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(n)`

---

# 26. 删除有序数组中的重复项

题目链接：https://leetcode.cn/problems/remove-duplicates-from-sorted-array/

## 题目描述

给定一个按非递减顺序排列的整数数组 `nums`，要求原地删除重复元素，使每个不同元素只出现一次，并保持原有顺序。

返回去重后不同元素的数量 `k`，并保证 `nums` 的前 `k` 个位置就是去重后的结果。

### 关键限制

- 数组已经有序。
- 必须原地修改数组。
- 只关心修改后数组的前 `k` 个元素。

### 必要示例

```text
输入：nums = [1,1,2]
返回：2
数组前 2 项变为：[1,2]
```

## 解法一：快慢指针原地覆盖（最优）

### 思路

因为数组有序，相同元素一定连续出现。

`slow` 指向当前去重结果的最后一个位置，`fast` 向右扫描。只要 `nums[fast] != nums[slow]`，就说明遇到了新元素，把它写到 `slow + 1`。

### Python 代码

```python
from typing import List


class Solution:
    def removeDuplicates(self, nums: List[int]) -> int:
        if not nums:
            return 0

        slow = 0

        for fast in range(1, len(nums)):
            if nums[fast] != nums[slow]:
                slow += 1
                nums[slow] = nums[fast]

        return slow + 1
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

> 本题在“数组有序 + 原地修改 + O(1) 额外空间”的要求下，主流最优方案本质就是双指针原地覆盖。其他常见写法大多只是同一思想的语法变体，或会退化为更差复杂度，因此不强行补一个低价值的第二解法。

---

# 27. 移除元素

题目链接：https://leetcode.cn/problems/remove-element/

来源：labuladong 双指针专题

## 题目描述

给定整数数组 `nums` 和整数 `val`，要求原地移除所有等于 `val` 的元素，并返回剩余元素的数量 `k`。

元素的相对顺序可以改变，只要求 `nums` 的前 `k` 个位置保存所有不等于 `val` 的元素。

### 关键限制

- 必须原地修改数组。
- 返回值是剩余元素个数 `k`。
- 前 `k` 个位置之外的内容不重要。

### 必要示例

```text
输入：nums = [3,2,2,3], val = 3
返回：2
数组前 2 项可以是：[2,2]
```

## 解法一：快慢指针原地覆盖（最优）

### 思路

`fast` 负责扫描所有元素，`slow` 指向“下一个应该写入保留元素的位置”。

只要 `nums[fast] != val`，就把它写到 `nums[slow]`，然后让 `slow += 1`。

### Python 代码

```python
from typing import List


class Solution:
    def removeElement(self, nums: List[int], val: int) -> int:
        slow = 0

        for fast in range(len(nums)):
            if nums[fast] != val:
                nums[slow] = nums[fast]
                slow += 1

        return slow
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：相向双指针，用尾部元素覆盖（同为 O(n)，写入次数可能更少）

### 思路

题目不要求保留相对顺序，因此遇到 `val` 时，可以直接拿数组末尾尚未处理的元素覆盖它。

这样当 `val` 很少时，写操作通常比稳定覆盖更少。

### Python 代码

```python
from typing import List


class Solution:
    def removeElement(self, nums: List[int], val: int) -> int:
        left = 0
        right = len(nums) - 1

        while left <= right:
            if nums[left] == val:
                nums[left] = nums[right]
                right -= 1
            else:
                left += 1

        return right + 1
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

---

# 1089. 复写零

题目链接：https://leetcode.cn/problems/duplicate-zeros/

来源：Algo-Atlas `Lc(1)双指针_1`

## 题目描述

给定一个定长整数数组 `arr`，每遇到一个 `0`，就要把这个 `0` 复制一次，并把其后的元素整体右移。

数组长度保持不变，超出原数组长度的元素直接丢弃。要求原地修改数组。

### 关键限制

- 数组长度不能改变。
- 每个 `0` 要在逻辑上出现两次。
- 不能因为从左往右移动而覆盖尚未处理的数据。

### 必要示例

```text
输入：arr = [1,0,2,3,0,4,5,0]
修改后：[1,0,0,2,3,0,0,4]
```

## 解法一：虚拟写指针 + 从右向左回填（最优）

### 思路

如果从左往右原地插入 `0`，会覆盖后面尚未处理的数据。

因此先计算“如果数组可以扩容，最后一个有效元素应该写到哪个虚拟位置”，再从右向左回填。写指针超出数组范围时只移动，不真正写入。

`read` 负责“我现在读原数组的哪个元素”。

`write` 负责“这个元素在复写后的逻辑数组里应该占到哪里”。

首先我们需要知道为了得到长度为n的最终结果数组，我们最多需要读到原数组的哪个元素？


### Python 代码

```python
class Solution:
    def duplicateZeros(self, arr: List[int]) -> None:
        n = len(arr)

        read = 0
        write = 0

        # 第一阶段：
        # 计算展开后需要读取到原数组哪里
        while write < n:
            if arr[read] == 0:
                write += 2
            else:
                write += 1

            read += 1

        # 回到最后一个真正需要处理的元素
        read -= 1
        write -= 1

        # 第二阶段：
        # 从后往前写，避免覆盖未读取数据
        while read >= 0:
            if arr[read] == 0:
                # 先写复写后的第二个0
                if write < n:
                    arr[write] = 0
                write -= 1

                # 再写原本对应的左边的 0
                if write < n:
                    arr[write] = 0
                write -= 1

            else:
                if write < n:
                    arr[write] = arr[read]
                write -= 1

            read -= 1
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：构造展开结果后截断（次优但直观）

### 思路

先把每个元素按规则写入一个新数组：普通元素写一次，`0` 写两次。最后只取前 `n` 个元素覆盖原数组。

### Python 代码

```python
from typing import List


class Solution:
    def duplicateZeros(self, arr: List[int]) -> None:
        expanded = []

        for x in arr:
            expanded.append(x)
            if x == 0:
                expanded.append(0)

        arr[:] = expanded[:len(arr)]
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(n)`

---

# 344. 反转字符串

题目链接：https://leetcode.cn/problems/reverse-string/

来源：labuladong 双指针专题

## 题目描述

给定字符数组 `s`，要求原地将字符顺序反转。

### 关键限制

- 必须直接修改输入数组。
- 目标额外空间复杂度为 `O(1)`。

### 必要示例

```text
输入：s = ["h","e","l","l","o"]
修改后：["o","l","l","e","h"]
```

## 解法一：相向双指针交换（最优）

### 思路

`left` 从左端开始，`right` 从右端开始。交换两端字符后同时向中间移动，直到两指针相遇。

### Python 代码

```python
from typing import List


class Solution:
    def reverseString(self, s: List[str]) -> None:
        left = 0
        right = len(s) - 1

        while left < right:
            s[left], s[right] = s[right], s[left]
            left += 1
            right -= 1
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：递归交换两端（次优，但能强化“双端收缩”模型）

### 思路

每一层递归交换当前最外层的一对字符，然后处理更小的区间 `[left + 1, right - 1]`。

它和双指针处理的是同一对称结构，但会产生递归栈，因此空间更差。

### Python 代码

```python
from typing import List


class Solution:
    def reverseString(self, s: List[str]) -> None:
        def dfs(left: int, right: int) -> None:
            if left >= right:
                return

            s[left], s[right] = s[right], s[left]
            dfs(left + 1, right - 1)

        dfs(0, len(s) - 1)
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(n)`，来自递归调用栈

---

# 125. 验证回文串

题目链接：https://leetcode.cn/problems/valid-palindrome/

## 题目描述

给定字符串 `s`，只考虑其中的字母和数字，并忽略大小写。判断处理后的字符串是否为回文串。

回文串指正着读和反着读都相同的字符串。

### 关键限制

- 非字母数字字符忽略。
- 字母大小写不区分。

### 必要示例

```text
输入："A man, a plan, a canal: Panama"
输出：true
```

## 解法一：相向双指针（最优）

### 思路

左右指针分别从字符串两端向中间移动。

如果当前字符不是字母或数字，就跳过；否则比较转成小写后的字符。只要有一次不同，就不是回文串。

### Python 代码

```python
class Solution:
    def isPalindrome(self, s: str) -> bool:
        left = 0
        right = len(s) - 1

        while left < right:
            while left < right and not s[left].isalnum():
                left += 1

            while left < right and not s[right].isalnum():
                right -= 1

            if s[left].lower() != s[right].lower():
                return False

            left += 1
            right -= 1

        return True
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：过滤后反转比较（次优但简洁）

### 思路

先构造一个只包含字母和数字、并全部转为小写的新字符串，然后与自己的逆序比较。

### Python 代码

```python
class Solution:
    def isPalindrome(self, s: str) -> bool:
        filtered = "".join(ch.lower() for ch in s if ch.isalnum())
        return filtered == filtered[::-1]
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(n)`

---

# 5. 最长回文子串(难)

题目链接：https://leetcode.cn/problems/longest-palindromic-substring/

来源：labuladong 双指针专题

## 题目描述

给定字符串 `s`，返回其中最长的回文子串。

回文串要求从左向右和从右向左读取完全相同。

### 关键限制

- 返回的是连续子串，不是子序列。
- 回文中心既可能是一个字符，也可能是两个字符之间的空隙。

### 必要示例

```text
输入：s = "babad"
输出："bab" 或 "aba"
```

## 解法一：中心扩展 + 相背双指针（最优主流）

### 思路

任何回文串都有中心。

枚举每个可能的中心，然后让 `left` 和 `right` 从中心向两侧扩张，只要字符相同就继续扩张，并维护最长区间。

每个位置都要考虑：

- 奇数长度中心 `(i, i)`
- 偶数长度中心 `(i, i + 1)`

### Python 代码

```python
class Solution:
    def longestPalindrome(self, s: str) -> str:
        best_left = 0
        best_right = 0

        def expand(left: int, right: int) -> None:
            nonlocal best_left, best_right

            while left >= 0 and right < len(s) and s[left] == s[right]:
                left -= 1
                right += 1

            left += 1
            right -= 1

            if right - left > best_right - best_left:
                best_left = left
                best_right = right

        for i in range(len(s)):
            expand(i, i)
            expand(i, i + 1)

        return s[best_left:best_right + 1]
```
另一种写法：

```py
class Solution:
    def longestPalindrome(self, s: str) -> str:
        start, end = 0, 0

        for i in range(len(s)):
            l1, r1 = self.palindrome(s, i, i)
            l2, r2 = self.palindrome(s, i, i + 1)

            if r1 - l1 > end - start:
                end = r1
                start = l1

            if r2 - l2 > end - start:
                end = r2
                start = l2
        
        return s[start:end+1]
            
    
    # 在s中寻找以s[l]和s[r]为中心的回文串
    def palindrome(self, s:str, l:int, r:int):
        while l >=0 and r < len(s) and s[l] == s[r]:
            l -= 1
            r += 1

        return l + 1, r - 1
```

### 复杂度分析

- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(1)`，不计算返回字符串

## 解法二：动态规划（同阶复杂度，状态定义很经典）

### 思路

定义：

```text
dp[i][j] = s[i:j+1] 是否为回文串
```

当 `s[i] == s[j]` 时，如果内部区间也是回文，当前区间就是回文。

### Python 代码

```python
class Solution:
    def longestPalindrome(self, s: str) -> str:
        n = len(s)
        dp = [[False] * n for _ in range(n)]

        best_left = 0
        best_len = 1

        for right in range(n):
            for left in range(right + 1):
                if s[left] == s[right] and (
                    right - left <= 2 or dp[left + 1][right - 1]
                ):
                    dp[left][right] = True

                    length = right - left + 1
                    if length > best_len:
                        best_left = left
                        best_len = length

        return s[best_left:best_left + best_len]
```

### 复杂度分析

- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(n^2)`




---

# 167. 两数之和 II - 输入有序数组

题目链接：https://leetcode.cn/problems/two-sum-ii-input-array-is-sorted/

## 题目描述

给定一个按非递减顺序排列的整数数组 `numbers` 和目标值 `target`，找出两个不同元素，使它们之和等于 `target`。

返回这两个元素的下标，题目要求使用从 `1` 开始的下标。

### 关键限制

- 输入数组已经有序。
- 每个测试用例恰好有一个答案。
- 同一个元素不能重复使用。

### 必要示例

```text
输入：numbers = [2,7,11,15], target = 9
输出：[1,2]
```

## 解法一：相向双指针（最优）

### 思路

设 `left` 指向最小值，`right` 指向最大值。

- 如果两数之和小于 `target`，说明左边太小，`left += 1`。
- 如果两数之和大于 `target`，说明右边太大，`right -= 1`。
- 相等时返回答案。

### Python 代码

```python
from typing import List


class Solution:
    def twoSum(self, numbers: List[int], target: int) -> List[int]:
        left = 0
        right = len(numbers) - 1

        while left < right:
            total = numbers[left] + numbers[right]

            if total < target:
                left += 1
            elif total > target:
                right -= 1
            else:
                return [left + 1, right + 1]

        return []
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：枚举一个数 + 二分查找

### 思路

枚举第一个元素 `numbers[i]`，目标就变成在右侧有序区间中查找 `target - numbers[i]`。

利用二分查找可以把第二个数的查找从线性降为对数时间。

### Python 代码

```python
from bisect import bisect_left
from typing import List


class Solution:
    def twoSum(self, numbers: List[int], target: int) -> List[int]:
        n = len(numbers)

        for i in range(n - 1):
            need = target - numbers[i]
            j = bisect_left(numbers, need, i + 1, n)

            if j < n and numbers[j] == need:
                return [i + 1, j + 1]

        return []
```

### 复杂度分析

- 时间复杂度：`O(n log n)`
- 空间复杂度：`O(1)`

---

# 2824. 统计和小于目标的下标对数目

题目链接：https://leetcode.cn/problems/count-pairs-whose-sum-is-less-than-target/

来源：灵茶山艾府「相向双指针（一）」课后题

## 题目描述

给定整数数组 `nums` 和整数 `target`，统计满足：

```text
0 <= i < j < n
nums[i] + nums[j] < target
```

的下标对数量。

### 关键限制

- 统计的是下标对数量。
- 相同数值出现在不同下标时，需要分别计数。

### 必要示例

```text
输入：nums = [-1,1,2,3,1], target = 2
输出：3
```

## 解法一：排序 + 相向双指针批量计数（最优主流）

### 思路

排序后，如果：

```text
nums[left] + nums[right] < target
```

那么固定 `left`，与 `left + 1 ... right` 中任意一个位置配对都一定满足条件，因此可以一次性增加：

```text
right - left
```

个答案。

### Python 代码

```python
from typing import List


class Solution:
    def countPairs(self, nums: List[int], target: int) -> int:
        arr = sorted(nums)
        left = 0
        right = len(arr) - 1
        ans = 0

        while left < right:
            if arr[left] + arr[right] < target:
                ans += right - left
                left += 1
            else:
                right -= 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n log n)`，排序占主导
- 空间复杂度：`O(n)`，这里使用 `sorted` 创建新数组

## 解法二：排序 + 二分查找每个左端点（同阶时间，另一种查边界思路）

### 思路

排序后，对每个 `i`，要寻找第一个满足：

```text
arr[j] >= target - arr[i]
```

的位置 `j`。

于是 `[i + 1, j)` 中的所有元素都能和 `arr[i]` 组成合法数对。

### Python 代码

```python
from bisect import bisect_left
from typing import List


class Solution:
    def countPairs(self, nums: List[int], target: int) -> int:
        arr = sorted(nums)
        ans = 0

        for i in range(len(arr)):
            j = bisect_left(arr, target - arr[i], i + 1)
            ans += j - i - 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n log n)`
- 空间复杂度：`O(n)`，这里使用 `sorted` 创建新数组

---

# 11. 盛最多水的容器

题目链接：https://leetcode.cn/problems/container-with-most-water/

## 题目描述

给定长度为 `n` 的整数数组 `height`。第 `i` 个元素表示一条竖线的高度，两条竖线和 x 轴可以组成一个容器。

选择两条竖线，使容器能够盛下的水最多，并返回最大容量。

### 关键限制

两条线位于下标 `i`、`j` 时，容器面积为：

```text
min(height[i], height[j]) * (j - i)
```

### 必要示例

```text
输入：height = [1,8,6,2,5,4,8,3,7]
输出：49
```

## 解法一：相向双指针（最优）

### 思路

左右指针从数组两端开始，每次计算当前面积。

面积受较短的那根柱子限制。如果移动较高的一侧，宽度变小，而短板没有改善，因此不可能得到更优结果。

所以每轮都移动较短的一侧。

### Python 代码

```python
from typing import List


class Solution:
    def maxArea(self, height: List[int]) -> int:
        left = 0
        right = len(height) - 1
        ans = 0

        while left < right:
            width = right - left
            h = min(height[left], height[right])
            ans = max(ans, width * h)

            if height[left] < height[right]:
                left += 1
            else:
                right -= 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：枚举所有两条线（次优但直观）

### 思路

枚举所有 `i < j` 的组合，计算对应容器面积并取最大值。

这是最直接的思路，但会重复考察大量不可能成为最优答案的组合。

### Python 代码

```python
from typing import List


class Solution:
    def maxArea(self, height: List[int]) -> int:
        ans = 0
        n = len(height)

        for i in range(n):
            for j in range(i + 1, n):
                area = min(height[i], height[j]) * (j - i)
                ans = max(ans, area)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(1)`

---

# 15. 三数之和

题目链接：https://leetcode.cn/problems/3sum/

## 题目描述

给定整数数组 `nums`，找出所有和为 `0` 的三元组 `[nums[i], nums[j], nums[k]]`。

三个下标必须互不相同，并且结果中不能包含重复三元组。

### 关键限制

- 返回的是元素值组成的三元组，而不是下标。
- 必须去重。

### 必要示例

```text
输入：nums = [-1,0,1,2,-1,-4]
输出：[[-1,-1,2],[-1,0,1]]
```

## 解法一：排序 + 枚举 + 相向双指针（最优 / 主流）

### 思路

先排序。

枚举第一个数 `nums[i]`，剩下的问题变成：在 `i` 右侧寻找两个数，使它们的和等于 `-nums[i]`。

这个两数问题可以用相向双指针在线性时间内完成，同时通过跳过相同值完成去重。

### Python 代码

```python
from typing import List


class Solution:
    def threeSum(self, nums: List[int]) -> List[List[int]]:
        nums.sort()
        ans = []
        n = len(nums)

        for i in range(n - 2):
            if i > 0 and nums[i] == nums[i - 1]:
                continue

            if nums[i] > 0:
                break

            left = i + 1
            right = n - 1

            while left < right:
                total = nums[i] + nums[left] + nums[right]

                if total < 0:
                    left += 1
                elif total > 0:
                    right -= 1
                else:
                    ans.append([nums[i], nums[left], nums[right]])
                    left += 1
                    right -= 1

                    while left < right and nums[left] == nums[left - 1]:
                        left += 1

                    while left < right and nums[right] == nums[right + 1]:
                        right -= 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(n)`（按 Python 排序可能使用的辅助空间计；不计答案）

## 解法二：枚举一个数 + 哈希集合

### 思路

固定 `i` 后，把剩余部分看成“两数之和”。

扫描 `j`，使用集合 `seen` 记录已经遇到的数。如果 `-nums[i] - nums[j]` 已经在集合中，就得到一个三元组。

为了避免重复答案，把三元组排序后放进结果集合。

### Python 代码

```python
from typing import List


class Solution:
    def threeSum(self, nums: List[int]) -> List[List[int]]:
        ans = set()
        n = len(nums)

        for i in range(n - 2):
            seen = set()

            for j in range(i + 1, n):
                need = -nums[i] - nums[j]

                if need in seen:
                    triplet = tuple(sorted((nums[i], nums[j], need)))
                    ans.add(triplet)

                seen.add(nums[j])

        return [list(triplet) for triplet in ans]
```

### 复杂度分析

- 时间复杂度：`O(n^2)`（三元组长度固定，内部排序视为 `O(1)`）
- 空间复杂度：`O(n + k)`，其中 `k` 为不同答案数量

---

# 16. 最接近的三数之和

题目链接：https://leetcode.cn/problems/3sum-closest/

## 题目描述

给定整数数组 `nums` 和整数 `target`，从数组中选出三个不同位置的元素，使三数之和与 `target` 最接近。

返回这个三数之和。

### 关键限制

- 每个输入保证存在唯一答案。
- 目标是最小化 `abs(sum - target)`。

### 必要示例

```text
输入：nums = [-1,2,1,-4], target = 1
输出：2
```

## 解法一：排序 + 相向双指针（最优）

### 思路

先排序，然后固定 `nums[i]`。

左右指针扫描剩余区间：

- 当前和小于 `target`，让 `left += 1`。
- 当前和大于 `target`，让 `right -= 1`。
- 每一步都更新当前最接近 `target` 的答案。

### Python 代码

```python
from typing import List


class Solution:
    def threeSumClosest(self, nums: List[int], target: int) -> int:
        nums.sort()
        best = nums[0] + nums[1] + nums[2]
        n = len(nums)

        for i in range(n - 2):
            left = i + 1
            right = n - 1

            while left < right:
                total = nums[i] + nums[left] + nums[right]

                if abs(total - target) < abs(best - target):
                    best = total

                if total < target:
                    left += 1
                elif total > target:
                    right -= 1
                else:
                    return target

        return best
```

### 复杂度分析

- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(n)`（按 Python 排序辅助空间计）

## 解法二：排序 + 枚举两数 + 二分第三个数

### 思路

排序后枚举前两个位置 `i`、`j`，需要寻找一个 `nums[k]`，使它尽可能接近：

```text
target - nums[i] - nums[j]
```

由于右侧区间有序，可以用二分查找最接近的位置，并检查插入点及其前一个位置。

### Python 代码

```python
from bisect import bisect_left
from typing import List


class Solution:
    def threeSumClosest(self, nums: List[int], target: int) -> int:
        nums.sort()
        n = len(nums)
        best = nums[0] + nums[1] + nums[2]

        for i in range(n - 2):
            for j in range(i + 1, n - 1):
                need = target - nums[i] - nums[j]
                k = bisect_left(nums, need, j + 1, n)

                for p in (k - 1, k):
                    if j < p < n:
                        total = nums[i] + nums[j] + nums[p]

                        if abs(total - target) < abs(best - target):
                            best = total

        return best
```

### 复杂度分析

- 时间复杂度：`O(n^2 log n)`
- 空间复杂度：`O(n)`（按 Python 排序辅助空间计）

---

# 18. 四数之和

题目链接：https://leetcode.cn/problems/4sum/

## 题目描述

给定整数数组 `nums` 和整数 `target`，找出所有不重复的四元组 `[nums[a], nums[b], nums[c], nums[d]]`，满足四个下标互不相同，并且四个元素之和等于 `target`。

答案中不能包含重复四元组。

### 关键限制

- 四个下标必须互不相同。
- 结果按元素值去重。
- 返回顺序不限。

### 必要示例

```text
输入：nums = [1,0,-1,0,-2,2], target = 0
输出：[[-2,-1,1,2],[-2,0,0,2],[-1,0,0,1]]
```

> 注意：上面的第三个四元组若写成 `[-1,0,0,1]`，需要数组中存在值 `1`，本例确实存在。常见标准答案也是这三个四元组。

## 解法一：排序 + 两层枚举 + 双指针（最优 / 主流）

### 思路

排序后枚举前两个数 `i`、`j`，剩下两个数用相向双指针寻找。

每一层都跳过重复值，从而避免生成重复四元组。

### Python 代码

```python
from typing import List


class Solution:
    def fourSum(self, nums: List[int], target: int) -> List[List[int]]:
        nums.sort()
        n = len(nums)
        ans = []

        for i in range(n - 3):
            if i > 0 and nums[i] == nums[i - 1]:
                continue

            for j in range(i + 1, n - 2):
                if j > i + 1 and nums[j] == nums[j - 1]:
                    continue

                left = j + 1
                right = n - 1

                while left < right:
                    total = nums[i] + nums[j] + nums[left] + nums[right]

                    if total < target:
                        left += 1
                    elif total > target:
                        right -= 1
                    else:
                        ans.append([nums[i], nums[j], nums[left], nums[right]])
                        left += 1
                        right -= 1

                        while left < right and nums[left] == nums[left - 1]:
                            left += 1

                        while left < right and nums[right] == nums[right + 1]:
                            right -= 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n^3)`
- 空间复杂度：`O(n)`（按 Python 排序辅助空间计；不计答案）

## 解法二：通用 K-Sum 递归 + 2Sum 双指针

### 思路

把“四数之和”抽象成通用 `kSum(start, k, target)`：

- 当 `k > 2` 时，枚举当前第一个数，再递归求剩余的 `k - 1` 个数。
- 当 `k == 2` 时，用双指针解决两数之和。

这种写法的价值在于可以自然推广到 `3Sum / 4Sum / 5Sum / ...`。

### Python 代码

```python
from typing import List


class Solution:
    def fourSum(self, nums: List[int], target: int) -> List[List[int]]:
        nums.sort()
        n = len(nums)

        def k_sum(start: int, k: int, target_sum: int) -> List[List[int]]:
            ans = []

            if n - start < k:
                return ans

            if k == 2:
                left = start
                right = n - 1

                while left < right:
                    total = nums[left] + nums[right]

                    if total < target_sum:
                        left += 1
                    elif total > target_sum:
                        right -= 1
                    else:
                        ans.append([nums[left], nums[right]])
                        left += 1
                        right -= 1

                        while left < right and nums[left] == nums[left - 1]:
                            left += 1

                        while left < right and nums[right] == nums[right + 1]:
                            right -= 1

                return ans

            i = start

            while i <= n - k:
                for rest in k_sum(i + 1, k - 1, target_sum - nums[i]):
                    ans.append([nums[i]] + rest)

                i += 1
                while i <= n - k and nums[i] == nums[i - 1]:
                    i += 1

            return ans

        return k_sum(0, 4, target)
```

### 复杂度分析

- 时间复杂度：`O(n^3)`（四数之和情况下）
- 空间复杂度：`O(n)`（排序辅助空间 + 递归栈；不计答案）

---

# 611. 有效三角形的个数

题目链接：https://leetcode.cn/problems/valid-triangle-number/

## 题目描述

给定一个由非负整数构成的数组 `nums`，统计可以从中选出多少组三个不同位置的元素，使这三个长度能够组成一个三角形。

### 关键限制

若三条边排序后满足：

```text
a <= b <= c
```

那么只需要检查：

```text
a + b > c
```

即可判断能否组成三角形。

### 必要示例

```text
输入：nums = [2,2,3,4]
输出：3
```

## 解法一：排序 + 固定最大边 + 相向双指针（最优）

### 思路

先排序，枚举最大边 `nums[k]`。

用 `left`、`right` 在 `k` 左侧寻找另外两条边：

- 若 `nums[left] + nums[right] > nums[k]`，那么 `left...right-1` 与 `right` 的组合全部成立，一次增加 `right - left` 个答案，然后 `right -= 1`。
- 否则说明最小边太小，`left += 1`。

### Python 代码

```python
from typing import List


class Solution:
    def triangleNumber(self, nums: List[int]) -> int:
        nums.sort()
        n = len(nums)
        ans = 0

        for k in range(n - 1, 1, -1):
            left = 0
            right = k - 1

            while left < right:
                if nums[left] + nums[right] > nums[k]:
                    ans += right - left
                    right -= 1
                else:
                    left += 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n^2)`
- 空间复杂度：`O(n)`（按 Python 排序辅助空间计）

## 解法二：排序 + 枚举两边 + 二分第三边

### 思路

排序后枚举前两条边 `i`、`j`。

需要找到最大的 `k`，满足：

```text
nums[k] < nums[i] + nums[j]
```

可以用二分查找第一个 `>= nums[i] + nums[j]` 的位置，那么 `j + 1` 到该位置前一个都能作为第三条边。

### Python 代码

```python
from bisect import bisect_left
from typing import List


class Solution:
    def triangleNumber(self, nums: List[int]) -> int:
        nums.sort()
        n = len(nums)
        ans = 0

        for i in range(n - 2):
            if nums[i] == 0:
                continue

            for j in range(i + 1, n - 1):
                limit = nums[i] + nums[j]
                k = bisect_left(nums, limit, j + 1, n)
                ans += k - j - 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n^2 log n)`
- 空间复杂度：`O(n)`（按 Python 排序辅助空间计）

---

# 42. 接雨水

题目链接：https://leetcode.cn/problems/trapping-rain-water/

## 题目描述

给定一个非负整数数组 `height`，其中每个元素表示宽度为 `1` 的柱子高度。计算这些柱子在下雨后最多能够接住多少单位的雨水。

### 关键限制

对于位置 `i`，能接到的水取决于：

```text
min(左侧最高柱, 右侧最高柱) - height[i]
```

只有这个值为正时才有积水。

### 必要示例

```text
输入：height = [0,1,0,2,1,0,1,3,2,1,2,1]
输出：6
```

## 解法一：双指针 + 左右最大值（最优）

### 思路

维护：

```text
left_max  = 左侧已经见过的最大高度
right_max = 右侧已经见过的最大高度
```

如果 `left_max <= right_max`，那么当前左侧位置能接多少水只由 `left_max` 决定，因为右侧至少存在一个不低于它的边界；于是结算 `left` 并右移。

反之结算 `right` 并左移。

### Python 代码

```python
from typing import List


class Solution:
    def trap(self, height: List[int]) -> int:
        left = 0
        right = len(height) - 1
        left_max = 0
        right_max = 0
        ans = 0

        while left <= right:
            if left_max <= right_max:
                left_max = max(left_max, height[left])
                ans += left_max - height[left]
                left += 1
            else:
                right_max = max(right_max, height[right])
                ans += right_max - height[right]
                right -= 1

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：单调栈

### 思路

维护一个从栈底到栈顶高度单调不增的下标栈。

当遇到一个比栈顶更高的柱子时，说明形成了一个“凹槽”：

1. 弹出的下标是凹槽底部。
2. 新栈顶是左边界。
3. 当前柱子是右边界。
4. 根据宽度和有效高度计算这一层能接的水。

### Python 代码

```python
from typing import List


class Solution:
    def trap(self, height: List[int]) -> int:
        stack = []
        ans = 0

        for i, h in enumerate(height):
            while stack and h > height[stack[-1]]:
                bottom = stack.pop()

                if not stack:
                    break

                left = stack[-1]
                width = i - left - 1
                bounded_height = min(height[left], h) - height[bottom]
                ans += width * bounded_height

            stack.append(i)

        return ans
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(n)`

---

# 2105. 给植物浇水 II

题目链接：https://leetcode.cn/problems/watering-plants-ii/

来源：灵茶山艾府「相向双指针（二）」课后题

## 题目描述

一排植物从左到右排列，Alice 从左端开始，Bob 从右端开始，两人同时向中间浇水。

两人各有一个固定容量的水壶；如果当前剩余水不足以浇下一株植物，就先回到各自水源把水壶装满，这会计作一次重新装水。

如果最后只剩同一株植物，两人中剩余水更多的人负责浇；若相同，则 Alice 负责。

返回两人总共重新装水的次数。

### 关键限制

- 两个人从数组两端相向移动。
- 是否补水取决于“浇当前植物之前”的剩余水量。
- 中间相遇时不能让两个人重复浇同一株植物。

### 必要示例

```text
输入：plants = [2,2,3,3], capacityA = 5, capacityB = 5
输出：1
```

## 解法一：相向双指针同步模拟（最优且唯一值得掌握的主流方案）

### 思路

用 `left`、`right` 表示 Alice 和 Bob 当前要浇的植物，用 `water_a`、`water_b` 保存两人当前剩余水量。

只要 `left < right`，就分别处理两端；最后如果 `left == right`，只检查剩余水更多的一方是否足够。

### Python 代码

```python
from typing import List


class Solution:
    def minimumRefill(
        self,
        plants: List[int],
        capacityA: int,
        capacityB: int,
    ) -> int:
        left = 0
        right = len(plants) - 1
        water_a = capacityA
        water_b = capacityB
        refills = 0

        while left < right:
            if water_a < plants[left]:
                refills += 1
                water_a = capacityA

            water_a -= plants[left]
            left += 1

            if water_b < plants[right]:
                refills += 1
                water_b = capacityB

            water_b -= plants[right]
            right -= 1

        if left == right and max(water_a, water_b) < plants[left]:
            refills += 1

        return refills
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

> 本题的核心就是“两个状态从两端向中间同步推进”。其他常见写法基本只是同一个模拟过程的代码变体，因此不为了凑 `optimal2` 强行加入低价值第二解法。

---

# 202. 快乐数

题目链接：https://leetcode.cn/problems/happy-number/

来源：Algo-Atlas `Lc(1)双指针_1`

## 题目描述

给定正整数 `n`，不断把它替换成“各位数字平方和”。

如果这个过程最终到达 `1`，则 `n` 是快乐数；如果进入一个不包含 `1` 的循环，则不是快乐数。

### 关键限制

- 关键不是模拟多少次，而是判断状态序列最终到达 `1` 还是进入环。
- 每个数字都唯一确定下一个状态，因此可以把过程看成一条隐式链表。

### 必要示例

```text
输入：n = 19
输出：true
```

## 解法一：快慢指针判环（最优空间）

### 思路

把：

```text
n -> 下一次平方和 -> 再下一次平方和 -> ...
```

看成一条隐式链表。

如果最终不是 `1`，状态序列一定会进入环，于是可以直接使用 Floyd 快慢指针判断。

**Floyd快慢指针判环算法：让一个慢指针一次走 1 步，一个快指针一次走 2 步；如果存在环，它们最终一定会在环里相遇。**

### Python 代码

```python
class Solution:
    def isHappy(self, n: int) -> bool:
        def next_number(x: int) -> int:
            total = 0

            while x > 0:
                digit = x % 10
                total += digit * digit
                x //= 10

            return total

        slow = next_number(n)
        fast = next_number(next_number(n))

        while fast != 1 and slow != fast:
            slow = next_number(slow)
            fast = next_number(next_number(fast))

        return fast == 1
```

### 复杂度分析

- 时间复杂度：`O(log n)` 量级；每次转换处理数字位数，且状态会很快落入一个有界范围
- 空间复杂度：`O(1)`

## 解法二：哈希集合记录访问状态（次优但最直观）

### 思路

把每次出现过的数字加入集合。

如果到达 `1`，返回 `True`；如果某个状态第二次出现，说明已经进入环，返回 `False`。

### Python 代码

```python
class Solution:
    def isHappy(self, n: int) -> bool:
        def next_number(x: int) -> int:
            total = 0

            while x > 0:
                digit = x % 10
                total += digit * digit
                x //= 10

            return total

        seen = set()

        while n != 1 and n not in seen:
            seen.add(n)
            n = next_number(n)

        return n == 1
```

### 复杂度分析

- 时间复杂度：`O(log n)` 量级
- 空间复杂度：`O(log n)` 的宽松上界，用于保存访问过的状态

---

# 83. 删除排序链表中的重复元素

题目链接：https://leetcode.cn/problems/remove-duplicates-from-sorted-list/

来源：labuladong 双指针专题；作为“数组双指针 → 链表指针”扩展题

## 题目描述

给定一个按非递减顺序排列的链表，删除其中重复节点，使每个值只保留一次，并返回去重后的链表。

### 关键限制

- 链表已经有序，因此相同值一定连续出现。
- 需要直接修改链表节点之间的连接关系。

### 必要示例

```text
输入：1 -> 1 -> 2 -> 3 -> 3
输出：1 -> 2 -> 3
```

## 解法一：迭代指针直接删除重复节点（最优）

### 思路

让 `cur` 指向当前保留节点。

如果 `cur.val == cur.next.val`，就让 `cur.next` 跳过重复节点；否则 `cur` 正常前进一步。

### Python 代码

```python
class Solution:
    def deleteDuplicates(self, head):
        cur = head

        while cur and cur.next:
            if cur.val == cur.next.val:
                cur.next = cur.next.next
            else:
                cur = cur.next

        return head
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(1)`

## 解法二：递归处理后缀（同阶时间，空间较差）

### 思路

先递归去重 `head.next` 开始的后缀，再比较当前 `head` 和已经去重后的下一个节点。

如果值相同，就返回 `head.next`；否则保留 `head`。

### Python 代码

```python
class Solution:
    def deleteDuplicates(self, head):
        if head is None or head.next is None:
            return head

        head.next = self.deleteDuplicates(head.next)

        if head.val == head.next.val:
            return head.next

        return head
```

### 复杂度分析

- 时间复杂度：`O(n)`
- 空间复杂度：`O(n)`，来自递归调用栈
