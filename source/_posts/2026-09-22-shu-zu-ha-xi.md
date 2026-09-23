---
title: "数组、哈希"
date: "2026-09-22 00:00:00"
permalink: "/2026/09/22/shu-zu-ha-xi/"
updated: "2026-09-22"
categories:
  - "数据结构与算法"
index_img: "/images/covers/defaults/data-structures-algorithms.webp"
---
## 原题干

给定整数数组 `nums` 和整数 `target`，请在数组中找到两个不同位置的元素，使它们的和等于 `target`，并返回这两个元素的下标。

题目保证存在唯一答案，并且同一个元素不能重复使用两次。

### 示例

```text
输入：nums = [2, 7, 11, 15], target = 9
输出：[0, 1]
```

```text
输入：nums = [3, 2, 4], target = 6
输出：[1, 2]
```

### 关键条件

- 返回的是下标。
- 同一个下标不能使用两次。
- 数组中可能出现重复值。

## 解法一：哈希表一次遍历

因为哈希表查询的时间复杂度为O(1)，故将问题从找两个数加起来等于九，转换成**当前拿着一个数，有没有另一个数和它加起来等于九？**

遍历到 `num` 时，需要寻找：

```python
need = target - num
```

用字典保存已经出现过的：

```text
元素值 -> 下标
```

如果 `need` 已经出现，就直接返回答案。

先查seen里有没有need，如果没有的话再把当前num存在哈希表中，避免把重复的元素值存储两个下标。

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}

        for i, num in enumerate(nums):
            need = target - num

            if need in seen:
                return [seen[need], i]

            seen[num] = i

        return []
```

**时间复杂度：** 平均 `O(n)`  
**空间复杂度：** `O(n)`

## 解法二：排序 + 双指针

先保存：

```text
(元素值, 原下标)
```

排序后使用左右双指针。

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        arr = sorted((num, i) for i, num in enumerate(nums))

        left = 0
        right = len(arr) - 1

        while left < right:
            total = arr[left][0] + arr[right][0]

            if total == target:
                return [arr[left][1], arr[right][1]]

            if total < target:
                left += 1
            else:
                right -= 1

        return []
```

**时间复杂度：** `O(n log n)`  
**空间复杂度：** `O(n)`

---

# 217. 存在重复元素

## 原题干

给定一个整数数组 `nums`。

如果数组中存在两个不同下标 `i` 和 `j`，满足：

```text
nums[i] == nums[j]
```

返回 `True`。

如果所有元素都互不相同，则返回 `False`。

### 示例

```text
输入：nums = [1, 2, 3, 1]
输出：True
```

```text
输入：nums = [1, 2, 3, 4]
输出：False
```

### 关键条件

- 只需要判断是否存在重复。
- 找到一个重复值即可立即返回。

## 解法一：哈希集合

遍历数组，用 `set` 记录已经出现的元素。

```python
class Solution:
    def containsDuplicate(self, nums: list[int]) -> bool:
        seen = set()

        for num in nums:
            if num in seen:
                return True

            seen.add(num)

        return False
```

**时间复杂度：** 平均 `O(n)`  
**空间复杂度：** `O(n)`

## 解法二：排序后比较相邻元素

排序以后，相同元素一定相邻。

```python
class Solution:
    def containsDuplicate(self, nums: list[int]) -> bool:
        nums.sort()

        for i in range(1, len(nums)):
            if nums[i] == nums[i - 1]:
                return True

        return False
```

**时间复杂度：** `O(n log n)`  
**空间复杂度：** Python `list.sort()` 最坏可能使用 `O(n)` 额外工作空间

---

# 242. 有效的字母异位词

## 原题干

给定两个字符串 `s` 和 `t`。

如果 `t` 可以通过重新排列 `s` 中的字符得到，并且每一种字符出现次数都完全相同，则返回 `True`；否则返回 `False`。

经典题设中字符串只包含小写英文字母。

### 示例

```text
输入：s = "anagram", t = "nagaram"
输出：True
```

```text
输入：s = "rat", t = "car"
输出：False
```

### 关键条件

- 字符顺序可以不同。
- 每种字符出现次数必须完全一致。
- 字符串长度不同可以直接返回 `False`。

## 解法一：26 位计数数组

因为只有小写英文字母，可以用长度为 26 的数组统计字符频率。

`ord()`把字符转换成Unicode编码对应的整数，`ord(ch) - ord('a')`可以把`'a' ~ 'z'` 映射成0-25的数组下标。

`all()`用于判断一组条件是不是全部为 True。

```python
class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
        if len(s) != len(t):
            return False

        count = [0] * 26

        for ch in s:
            count[ord(ch) - ord('a')] += 1

        for ch in t:
            count[ord(ch) - ord('a')] -= 1

        return all(x == 0 for x in count)
```

**时间复杂度：** `O(n)`  
**空间复杂度：** `O(1)`

## 解法二：排序

两个字符串如果互为异位词，那么排序后一定完全相同。

```python
class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
        return sorted(s) == sorted(t)
```

**时间复杂度：** `O(n log n)`  
**空间复杂度：** `O(n)`

---

# 49. 字母异位词分组

## 原题干

给定一个字符串数组 `strs`，请把所有互为字母异位词的字符串放到同一组。

字母异位词指：

> 两个字符串包含相同种类、相同数量的字符，只是排列顺序不同。

返回结果中，各组之间以及组内顺序都不作要求。

### 示例

```text
输入：
["eat", "tea", "tan", "ate", "nat", "bat"]

一种合法输出：
[
    ["eat", "tea", "ate"],
    ["tan", "nat"],
    ["bat"]
]
```

### 关键条件

- 同一组中的字符串必须有完全相同的字符频率。
- 需要为每个字符串构造一个稳定且可哈希的分组 key。

## 解法一：字符频率 tuple 作为 key

对于小写英文字母，可以统计 26 个字母的频率。

同一组异位词会得到完全相同的 26 位频率。

`defaultdict()`相当于一个自带默认值的字典，假如没有value，会自动填充一个输入参数作为默认值。

不用list当字典 key，是因为 list 是可变对象，不能被哈希，必须使用元组。

```python
from collections import defaultdict


class Solution:
    def groupAnagrams(self, strs: list[str]) -> list[list[str]]:
        groups = defaultdict(list)

        for s in strs:
            count = [0] * 26

            for ch in s:
                count[ord(ch) - ord('a')] += 1

            key = tuple(count)
            groups[key].append(s)

        return list(groups.values())
```

设：

- `m` = 字符串数量
- `k` = 单个字符串最大长度

**时间复杂度：** `O(m * k)`  
**空间复杂度：** `O(m * k)`（包括分组结果与 key 存储）

## 解法二：排序后的字符串作为 key

异位词排序后结果完全相同，因此可以把排序结果作为 key。

```python
from collections import defaultdict


class Solution:
    def groupAnagrams(self, strs: list[str]) -> list[list[str]]:
        groups = defaultdict(list)

        for s in strs:
            key = ''.join(sorted(s))
            groups[key].append(s)

        return list(groups.values())
```

**时间复杂度：** `O(m * k log k)`  
**空间复杂度：** `O(m * k)`

---

# 128. 最长连续序列

## 原题干

给定一个未排序的整数数组 `nums`，请找出最长连续整数序列的长度。

这里的“连续”指的是数值连续，例如：

```text
1, 2, 3, 4
```

而不要求这些数字在原数组中的位置相邻。

经典进阶要求是实现平均 `O(n)` 时间复杂度。

### 示例

```text
输入：nums = [100, 4, 200, 1, 3, 2]
输出：4

解释：
最长连续序列为 [1, 2, 3, 4]
```

```text
输入：nums = [0, 3, 7, 2, 5, 8, 4, 6, 0, 1]
输出：9
```

### 关键条件

- 原数组无序。
- 数组可能包含重复元素。
- 连续指数值连续，不是位置连续。

## 解法一：哈希集合 + 只从序列起点扩展

把所有数字放入 `set`，这样查找某个数的平均时间复杂度是$O(1)$,可以一直检查。

如果：

```python
num - 1 not in num_set
```

说明 `num` 是某段连续序列的起点。

只从起点向右扩展。

```python
class Solution:
    def longestConsecutive(self, nums: list[int]) -> int:
        num_set = set(nums)
        longest = 0

        for num in num_set:
            # 找到连续序列的起点
            if num - 1 not in num_set:
                current = num
                length = 1

                while current + 1 in num_set:
                    current += 1
                    length += 1

                longest = max(longest, length)

        return longest
```

**时间复杂度：** 平均 `O(n)`  
**空间复杂度：** `O(n)`

## 解法二：排序后线性扫描

排序后，连续数字会排在一起。

重复数字不增加连续序列长度。

```python
class Solution:
    def longestConsecutive(self, nums: list[int]) -> int:
        if not nums:
            return 0

        nums.sort()

        longest = 1
        current = 1

        for i in range(1, len(nums)):
            if nums[i] == nums[i - 1]:
                continue

            if nums[i] == nums[i - 1] + 1:
                current += 1
            else:
                current = 1

            longest = max(longest, current)

        return longest
```

**时间复杂度：** `O(n log n)`  
**空间复杂度：** Python 排序最坏可能使用 `O(n)` 额外工作空间

---

# 169. 多数元素

## 原题干

给定长度为 `n` 的整数数组 `nums`。

数组中保证存在一个多数元素。

多数元素指：

```text
出现次数严格大于 n / 2 的元素
```

请返回这个元素。

### 示例

```text
输入：nums = [3, 2, 3]
输出：3
```

```text
输入：nums = [2, 2, 1, 1, 1, 2, 2]
输出：2
```

### 关键条件

- 多数元素一定存在。
- 出现次数严格超过数组长度的一半。

## 解法一：Boyer-Moore 投票算法

多数元素的出现超过一半，这意味着**它可以和所有其他元素“一对一抵消”，最后仍然剩下来。**

Boyer-Moore 算法的详细步骤：

- 我们维护一个候选众数 candidate 和它出现的次数 count。初始时 candidate 可以为任意值，count 为 0；

- 我们遍历数组 nums 中的所有元素，对于每个元素 x，在判断 x 之前，如果 count 的值为 0，我们先将 x 的值赋予 candidate，随后我们判断 x：

    - 如果 x 与 candidate 相等，那么计数器 count 的值增加 1；

    - 如果 x 与 candidate 不等，那么计数器 count 的值减少 1。

- 在遍历完成后，candidate 即为整个数组的众数。



```python
class Solution:
    def majorityElement(self, nums: list[int]) -> int:
        candidate = None
        count = 0

        for num in nums:
            if count == 0:
                candidate = num

            if num == candidate:
                count += 1
            else:
                count -= 1

        return candidate
```

**时间复杂度：** `O(n)`  
**空间复杂度：** `O(1)`

## 解法二：哈希表计数

统计每个元素出现次数，一旦超过 `n // 2` 就返回。

```python
class Solution:
    def majorityElement(self, nums: list[int]) -> int:
        count = {}
        threshold = len(nums) // 2

        for num in nums:
            count[num] = count.get(num, 0) + 1

            if count[num] > threshold:
                return num

        return nums[0]
```

**时间复杂度：** 平均 `O(n)`  
**空间复杂度：** `O(n)`

---

# 41. 缺失的第一个正数

## 原题干

给定一个未排序的整数数组 `nums`。

数组中可能包含：

- 正数
- `0`
- 负数
- 重复数字

请返回数组中没有出现过的最小正整数。

经典进阶要求：

```text
时间复杂度：O(n)
额外空间复杂度：O(1)
```

### 示例

```text
输入：nums = [1, 2, 0]
输出：3
```

```text
输入：nums = [3, 4, -1, 1]
输出：2
```

```text
输入：nums = [7, 8, 9, 11, 12]
输出：1
```

### 关键条件

如果数组长度为 `n`，答案一定在：

```text
[1, n + 1]
```

因为：

- 如果 `1 ~ n` 全部存在，答案就是 `n + 1`。
- 否则答案一定是 `1 ~ n` 中缺失的某一个值。

## 解法一：原地哈希 / 循环置换

对于所有位于 `1 ~ n` 的数字，可以规定：

```text
数字 x 应该放在下标 x - 1
```

于是理想情况下应该满足：

```text
nums[i] == i + 1
```

把合法数字尽量交换到正确位置，最后从左到右找第一个不匹配的位置。

```python
class Solution:
    def firstMissingPositive(self, nums: list[int]) -> int:
        n = len(nums)

        # 把 1~n 范围内的数字放到对应位置
        for i in range(n):
            while (
                1 <= nums[i] <= n
                and nums[nums[i] - 1] != nums[i]  # 确保目标位置没有相同数字，否则会陷入死循环
            ):
                index = nums[i] - 1

                nums[i], nums[index] = nums[index], nums[i]

        # 找第一个位置不正确的地方
        for i in range(n):
            if nums[i] != i + 1:
                return i + 1

        return n + 1
```

**时间复杂度：** `O(n)`  
**空间复杂度：** `O(1)`

## 解法二：哈希集合

先把所有数字放入集合，再从 `1` 开始查找第一个不存在的正整数。

```python
class Solution:
    def firstMissingPositive(self, nums: list[int]) -> int:
        num_set = set(nums)

        for x in range(1, len(nums) + 2):
            if x not in num_set:
                return x

        return 1
```

**时间复杂度：** 平均 `O(n)`  
**空间复杂度：** `O(n)`

## 解法三：正负号标记法

- 先处理无关数字：我们只关心 1-n，所以小于等于0的数字直接改成n+1。
- 把数组当哈希表：规定 nums[i] 的正负 -> 数字 i+1 出没出现，如果 i+1 出现，那么 nums[i] 就为负数。
- 读取时使用abs()

```py
class Solution:
    def firstMissingPositive(self, nums: list[int]) -> int:
        n = len(nums)

        # 第一步：处理 <= 0 的无关数字
        for i in range(n):
            if nums[i] <= 0:
                nums[i] = n + 1

        # 第二步：利用正负号标记数字是否出现
        for i in range(n):
            num = abs(nums[i])

            if 1 <= num <= n:
                index = num - 1

                nums[index] = -abs(nums[index])

        # 第三步：找到第一个没有被标记的位置
        for i in range(n):
            if nums[i] > 0:
                return i + 1

        return n + 1
```

- 时间复杂度：O(n)
- 空间复杂度: O(1)

# 总结

## 查找规则

- 知道位置 -> `list[index]`：O(1)
- 不知道位置，只想判断是否存在：`set()`， 平均 O(1)
- 不知道位置，而且还需要这个值对应的信息： `dict`, 平均 O(1)


## 必背骨架

```py
# 1. dict 查补数
need = target - num
if need in seen:
    ...

# 2. set 查重
if num in seen:
    ...
seen.add(num)

# 3. 频率数组
count[ord(ch) - ord('a')] += 1

# 4. tuple 作为哈希 key
key = tuple(count)

# 5. 连续序列只找起点
if num - 1 not in num_set:
    ...

# 6. Boyer-Moore
if count == 0:
    candidate = num

count += 1 if num == candidate else -1

# 7. 原地哈希
while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
    ...

# 8. 正负号标记
nums[num - 1] = -abs(nums[num - 1])
```
