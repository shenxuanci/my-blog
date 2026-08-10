---
title: "py学习笔记"
date: "2026-07-23"
updated: "2026-08-09"
categories:
  - "技术学习"
index_img: "/images/covers/custom/20260723014916-qq-jie-tu-20260723014829.webp"
---
## 一、基础语法与数据类型

### 1. 变量、赋值与命名

py是动态类型语言，变量本身不固定保存某一种类型，它更像是一个名字，运行时绑定到某个对象。

```py
name = "Alice"
age = 20
pi = 3.14159
is_student = True
```

变量名常用命名规则：

- 只能由字母、数字和下划线组成，不能以数字开头
- 区分大小写，`name`和`Name`是两个不同的变量
- 变量、函数通常使用`snake_case`
- 类名通常使用`PascalCase`
- 常量没有语法层面的强制限制，约定使用`UPPER_CASE`

例如：

```py
user_name = "Alice"
MAX_RETRY = 3

class UserProfile:
    pass
```

py支持多重赋值和交换变量：

```py
a, b = 1, 2
a, b = b, a

print(a, b)  # 2 1
```

赋值不会自动复制对象。例如：

```py
a = [1, 2, 3]
b = a

b.append(4)
print(a)  # [1, 2, 3, 4]
```

此时`a`和`b`都绑定到同一个列表对象。

### 2. 常见基本类型

常见内置类型：

| 类型 | 示例 | 说明 |
|---|---|---|
| `int` | `10` | 整数 |
| `float` | `3.14` | 浮点数 |
| `bool` | `True`、`False` | 布尔值 |
| `str` | `"hello"` | 字符串 |
| `NoneType` | `None` | 表示“没有值” |
| `list` | `[1, 2]` | 可变序列 |
| `tuple` | `(1, 2)` | 不可变序列 |
| `dict` | `{"name": "Alice"}` | 键值映射 |
| `set` | `{1, 2, 3}` | 无重复元素集合 |

可以使用`type()`查看对象类型：

```py
x = 10
print(type(x))  # <class 'int'>
```

需要判断一个对象是否属于某种类型时，工程代码中通常优先使用`isinstance()`：

```py
value = 10

if isinstance(value, int):
    print("value是整数")
```

`isinstance()`还会正确处理继承关系。

### 3. 数值运算

常见运算符：

```py
a + b   # 加

a - b   # 减

a * b   # 乘

a / b   # 真除法，通常返回float

a // b  # 向下取整除法

a % b   # 取余

a ** b  # 幂
```

例如：

```py
print(7 / 2)   # 3.5
print(7 // 2)  # 3
print(7 % 2)   # 1
print(2 ** 3)  # 8
```

复合赋值：

```py
x = 10
x += 1
x *= 2
```

### 4. 比较、逻辑与成员运算

比较运算：

```py
==
!=
<
<=
>
>=
```

逻辑运算：

```py
and
or
not
```

成员运算：

```py
in
not in
```

例如：

```py
nums = [1, 2, 3]

print(2 in nums)      # True
print(5 not in nums)  # True
```

`is`和`==`不要混淆：

- `==`通常比较两个对象的值是否相等
- `is`比较两个变量是否指向同一个对象

```py
a = [1, 2]
b = [1, 2]
c = a

print(a == b)  # True
print(a is b)  # False
print(a is c)  # True
```

判断`None`时通常写：

```py
if value is None:
    ...
```

而不是`value == None`。

### 5. 真值判断

在`if`、`while`等条件中，py会把对象转换为布尔意义上的真假。

常见假值包括：

```py
False
None
0
0.0
""
[]
{}
set()
()
```

例如：

```py
items = []

if not items:
    print("列表为空")
```

因此一般不需要写：

```py
if len(items) == 0:
    ...
```

### 6. 类型转换

常见转换函数：

```py
int("123")
float("3.14")
str(100)
bool(1)
list((1, 2, 3))
tuple([1, 2, 3])
set([1, 1, 2])
```

需要注意，类型转换可能失败：

```py
int("abc")  # ValueError
```

因此处理外部输入时通常需要进行校验或异常处理。

### 7. 字符串基础与f-string

字符串可以使用单引号、双引号或三引号：

```py
s1 = 'hello'
s2 = "world"
s3 = """这是一个
多行字符串"""
```

字符串是不可变对象，对字符串执行“修改”操作通常会产生新字符串。

现代py中推荐使用f-string进行格式化：

```py
name = "Alice"
age = 20

message = f"我是{name}，今年{age}岁"
print(message)
```

格式控制：

```py
pi = 3.1415926
print(f"{pi:.2f}")  # 3.14
```

### 8. 解包与星号表达式

序列解包：

```py
point = (10, 20)
x, y = point
```

可以使用`*`接收剩余元素：

```py
first, *middle, last = [1, 2, 3, 4, 5]

print(first)   # 1
print(middle)  # [2, 3, 4]
print(last)    # 5
```

`*`也可以展开可迭代对象：

```py
a = [1, 2]
b = [3, 4]

combined = [*a, *b]
print(combined)  # [1, 2, 3, 4]
```

`**`可以展开字典：

```py
base = {"name": "Alice", "age": 20}
updated = {**base, "age": 21}

print(updated)
```

后面的键会覆盖前面同名的键。

## 二、常用容器

### 1. `list` 列表

列表是有顺序、可修改的序列：

```py
nums = [10, 20, 30]

print(nums[0])   # 10
print(nums[-1])  # 30
```

常见操作：

```py
nums.append(40)
nums.extend([50, 60])
nums.insert(1, 15)
nums.remove(20)
last = nums.pop()
```

切片：

```py
nums = [0, 1, 2, 3, 4, 5]

print(nums[1:4])   # [1, 2, 3]
print(nums[:3])    # [0, 1, 2]
print(nums[::2])   # [0, 2, 4]
print(nums[::-1])  # 反转后的新列表
```

注意：普通切片会创建一个新的列表，但列表中的元素如果本身是可变对象，仍可能共享内部对象引用。

### 2. `tuple` 元组

元组是不可变序列：

```py
point = (10, 20)
```

单元素元组必须保留逗号：

```py
single = (1,)
```

元组常用于：

- 表示不应该被修改的一组值
- 多返回值
- 字典键（前提是其中元素也可哈希）

函数所谓的“返回多个值”，本质上通常是返回一个元组：

```py
def get_point():
    return 10, 20

x, y = get_point()
```

### 3. `dict` 字典

字典保存键值对：

```py
user = {
    "name": "Alice",
    "age": 20,
}
```

访问和修改：

```py
print(user["name"])
user["age"] = 21
user["city"] = "Beijing"
```

若键可能不存在，使用`get()`更安全：

```py
city = user.get("city", "未知")
```

遍历：

```py
for key in user:
    print(key)

for key, value in user.items():
    print(key, value)
```

常用方法：

```py
user.keys()
user.values()
user.items()
user.pop("age")
```

### 4. `set` 集合

集合中的元素不会重复，常用于去重和快速成员判断：

```py
nums = {1, 2, 3}
nums.add(4)
nums.discard(2)
```

空集合必须使用：

```py
empty = set()
```

因为：

```py
{}  # 这是空字典
```

集合运算：

```py
a = {1, 2, 3}
b = {3, 4, 5}

print(a | b)  # 并集
print(a & b)  # 交集
print(a - b)  # 差集
print(a ^ b)  # 对称差集
```

### 5. 可变对象与不可变对象

常见不可变对象：

- `int`
- `float`
- `bool`
- `str`
- `tuple`（前提是内部对象本身不被修改）
- `frozenset`

常见可变对象：

- `list`
- `dict`
- `set`
- 大多数自定义类实例

这个区别会直接影响：

- 函数传参后的修改效果
- 是否能作为`dict`的键
- 是否能放入`set`
- 浅拷贝/深拷贝行为

### 6. 浅拷贝与深拷贝

对于嵌套可变对象，仅复制最外层容器时，内部对象仍然会共享引用：

```py
original = [[1, 2], [3, 4]]
shallow = original.copy()

shallow[0].append(99)
print(original)  # [[1, 2, 99], [3, 4]]
```

需要递归复制内部对象时，可以使用：

```py
import copy

deep = copy.deepcopy(original)
```

但深拷贝并不是任何场景都应该默认使用；工程代码中更重要的是明确对象所有权和是否需要共享状态。

## 三、控制流

### 1. `if / elif / else`

```py
score = 85

if score >= 90:
    print("A")
elif score >= 80:
    print("B")
else:
    print("C")
```

条件表达式（三元表达式）：

```py
status = "通过" if score >= 60 else "不通过"
```

### 2. `for` 循环

py中的`for`通常不是“按下标循环”，而是直接从可迭代对象中依次取值：

```py
for item in [10, 20, 30]:
    print(item)
```

需要下标时使用`enumerate()`：

```py
for index, item in enumerate([10, 20, 30]):
    print(index, item)
```

同时遍历多个序列可以使用`zip()`：

```py
names = ["Alice", "Bob"]
scores = [90, 80]

for name, score in zip(names, scores):
    print(name, score)
```

### 3. `while`、`break`、`continue`

```py
count = 0

while count < 5:
    count += 1

    if count == 2:
        continue

    if count == 4:
        break

    print(count)
```

- `break`：立即结束当前循环
- `continue`：跳过本轮剩余代码，进入下一轮

循环还支持`else`：

```py
for number in [1, 3, 5]:
    if number % 2 == 0:
        print("找到偶数")
        break
else:
    print("没有找到偶数")
```

这里的`else`只有在循环**没有被break提前结束**时才执行。

### 4. `match / case`（Python 3.10+）

结构化模式匹配适合处理具有明确形状的多分支数据：

```py
def handle_command(command):
    match command:
        case ["quit"]:
            return "退出"
        case ["open", filename]:
            return f"打开文件：{filename}"
        case ["move", x, y]:
            return f"移动到：{x}, {y}"
        case _:
            return "未知命令"
```

不要把`match`简单理解成其他语言的`switch`。它不仅能比较固定值，还可以对列表、元组、字典、类等结构进行模式匹配。

### 5. `pass`

`pass`表示什么都不做，常用于暂时占位：

```py
def todo():
    pass
```

## 四、函数参数：`*args` 与 `**kwargs`

### 1. 可变位置参数 `*args`

*args将传入的位置参数打包为一个元组

```py
def sum_all(*args):
    print(f"args的类型: {type(args)}")  # <class 'tuple'>
    print(f"args的内容: {args}")        # (1, 2, 3, 4)
    return sum(args)

print(sum_all(1, 2, 3, 4))  # 输出: 10
```

```py
def print_names(*args):
    for i, name in enumerate(args, 1):  
        print(f"{i}. {name}")

print_names("小明", "小红", "小华")
# 输出:
# 1. 小明
# 2. 小红
# 3. 小华
```
注：enumerate() 是 Python 内置函数，用于在遍历可迭代对象时同时获取索引和值。

### 2. 可变关键字参数 `**kwargs`

**kwargs 将传入的关键字参数打包成一个字典

```py
def show_info(**kwargs):
    print(f"kwargs的类型: {type(kwargs)}")  # <class 'dict'>
    print(f"kwargs的内容: {kwargs}")        # {'name': '张三', 'age': 25, 'city': '北京'}
    
    for key, value in kwargs.items():
        print(f"{key}: {value}")

show_info(name="张三", age=25, city="北京")
# 输出:
# name: 张三
# age: 25
# city: 北京
```

### 3. 混合使用与参数顺序

在这个例子中，参数顺序是：普通参数 → *args → 仅限关键字参数 → **kwargs

其中，写在`*args`后面的`default`只能通过关键字传入，因此属于仅限关键字参数。

```py
def mixed(param1, param2, *args, default="默认值", **kwargs):
    print(f"普通参数: {param1}, {param2}")
    print(f"*args: {args}")
    print(f"默认参数: {default}")
    print(f"**kwargs: {kwargs}")

mixed(1, 2, 3, 4, 5, default="自定义", name="李四", age=30)
# 输出:
# 普通参数: 1, 2
# *args: (3, 4, 5)
# 默认参数: 自定义
# **kwargs: {'name': '李四', 'age': 30}
```


### 4. 位置参数、关键字参数与 `/`、`*`

除了`*args`和`**kwargs`，py还可以显式限制参数的传递方式。

#### 位置参数与关键字参数

```py
def greet(name, message="你好"):
    print(f"{message}，{name}")

# 位置参数
greet("Alice", "欢迎")

# 关键字参数
greet(name="Alice", message="欢迎")
```

#### 仅限位置参数：`/`

`/`前面的参数只能按位置传入：

```py
def divide(a, b, /):
    return a / b

divide(10, 2)        # 正确
# divide(a=10, b=2)  # TypeError
```

#### 仅限关键字参数：`*`

单独的`*`之后的参数只能通过关键字传入：

```py
def connect(host, *, timeout=5, retry=3):
    print(host, timeout, retry)

connect("example.com", timeout=10, retry=2)
```

完整参数顺序可以理解为：

```text
仅限位置参数 / 普通参数 / *args / 仅限关键字参数 / **kwargs
```

实际代码中不一定需要把所有形式同时用上，但读标准库、FastAPI或第三方SDK时经常会看到`/`和`*`。

### 5. 调用函数时的 `*` 与 `**` 解包

`*args`和`**kwargs`不仅可以出现在函数定义中，也可以用于函数调用时展开参数：

```py
def add(a, b, c):
    return a + b + c

nums = [1, 2, 3]
print(add(*nums))  # 等价于 add(1, 2, 3)
```

字典可以通过`**`展开成关键字参数：

```py
def show(name, age):
    print(name, age)

info = {"name": "Alice", "age": 20}
show(**info)
```

## 五、函数进阶

### 1. 函数也是对象

在py中，函数是一个真正的对象。能够在后面加`()`进行调用的对象，称为可调用对象。

所以函数可以作为值赋给变量，也可以作为参数传递，也可以作为返回值。

装饰器能够成立，其根本原因为：

>函数可以接收另一个函数，也可以返回一个新函数

### 2. lambda 表达式（匿名函数）

lambda真正适合的场景是：

>某个地方需要传入一个简单函数，而这个函数只用一次。

**注：** 下面部分代码主要用于展示lambda支持的各种参数形式。实际编程中，如果一个函数需要起名字并反复使用，通常更推荐使用`def`；lambda更适合临时作为其他函数的参数使用。

#### 基本语法

```py
lambda 接收参数列表: 返回值表达式
```

冒号后面的表达式计算出什么，函数就自动返回什么。

注：函数调用也属于表达式，所以你也可以在返回值表达式里调用一个函数，那么lambda就会返回这个函数的返回值。

因为py中函数也是对象，所以lambda还可以返回一个函数，就像下面这样：

```py
create_multiplier = lambda number: lambda value: value * number
```

这个写法会形成闭包，闭包将在后面详细讲解。它等价于：

```py
def create_multiplier(number):
    def multiply(value):
        return value * number

    return multiply
```

#### lambda 函数的调用方式

##### a. 先保存，再调用

```py
double = lambda x: x * 2
# 这里lambda表达式会创建一个函数对象，然后变量double指向这个函数
result = double(10)

print(result)
```
##### b. 创建后立即调用

```py
result = (lambda x: x * 2)(10)

print(result)
```

#### 参数形式

##### a. 单个参数

```py
# 基本运算
square = lambda x: x ** 2
print(square(5))  # 输出: 25

# 字符串处理
to_upper = lambda s: s.upper()
print(to_upper("hello"))  # 输出: HELLO

# 类型转换
to_int = lambda s: int(s) if s.isdigit() else 0
print(to_int("123"))  # 输出: 123
print(to_int("abc"))  # 输出: 0
```

##### b. 多个参数

```py
# 两个参数
add = lambda x, y: x + y
print(add(10, 20))  # 输出: 30

# 三个参数
multiply_three = lambda x, y, z: x * y * z
print(multiply_three(2, 3, 4))  # 输出: 24

# 多个参数做复杂操作
distance = lambda x1, y1, x2, y2: ((x2 - x1)**2 + (y2 - y1)**2)**0.5
print(distance(0, 0, 3, 4))  # 输出: 5.0

# 计算 BMI
bmi = lambda weight, height: weight / (height ** 2)
print(bmi(70, 1.75))  # 输出: 22.86
```

##### c. 默认参数
```py
# 带默认参数的 lambda
greet = lambda name, greeting="Hello": f"{greeting}, {name}!"
print(greet("Alice"))           # 输出: Hello, Alice!
print(greet("Bob", "Hi"))       # 输出: Hi, Bob!

# 默认参数做计算
power = lambda x, exp=2: x ** exp
print(power(5))     # 输出: 25
print(power(2, 3))  # 输出: 8

# lambda的默认参数规则和def相同，因此同样存在“可变默认参数”陷阱。
# 为了避免把这个陷阱和lambda的表达式写法混在一起，下面用def展示这个反例。
def add_item(item=0, lst=[]):
    lst.append(item)
    return lst

print(add_item(3, [1, 2]))  # 输出: [1, 2, 3]
print(add_item(item=5))     # 输出: [5]
print(add_item(item=10))    # 输出: [5, 10]  # 注意：默认列表会被重复使用
```

##### d. 无参数

```py
# 无参数
get_five = lambda: 5
print(get_five())  # 输出: 5

# 无参数lambda也可以调用函数
import time
get_current_time = lambda: time.time()
print(get_current_time())

# 立即执行的无参数 lambda
result = (lambda: 3.14159)()
print(result)  # 输出: 3.14159
```

### 3. 闭包

闭包就是：

>内部函数引用了外部函数的变量，即使外部函数已经执行完毕，内部函数仍然保留着这些变量所处的环境。

从更准确的角度说，闭包是：

**内部函数，加上它所记住的外部变量。**

例如：

```py
def outer():
    message = "你好"

    def inner():
        print(message)

    return inner
# 调用：
func = outer()
func()
# 输出：你好
```

执行过程：

1. 调用外层函数：
    ```py
    func = outer()
    ```

    py此时进入`outer()`：
    ```py
    message = "你好"
    ```

    然后创建内部函数：
    ```py
    def inner():
        print(message)
    ```

    最后：
    ```py
    return inner
    ```

    注意到不是`return inner()`，`inner()`表示立即调用函数，而`inner`表示函数对象本身

    故`func = outer()`实际上可以理解为`func = inner`
2. 调用内部函数：
    `func()`相当于调用`inner()` ，而`inner()`中需要使用`message`，但是`inner`自己内部没有定义`message`，于是它会去外层寻找，然后找到`message = "你好"`。
    虽然`outer()`已经运行结束，但是`inner`仍然保存着对这个变量的引用，因此可以继续使用它。

#### 闭包的基本条件

一般需要同时满足下面三个条件：

1. 存在一个外层函数
2. 外层函数里面定义了一个内层函数
3. 内层函数使用了外层函数的变量。被返回或传递出去不是闭包成立的必要条件，但这样最能体现外层函数结束后变量仍被保存


#### `nonlocal` 的作用

```py
def create_counter():
    count = 0

    def counter():
        count += 1
        return count

    return counter

# 运行后会报错：UnboundLocalError
```

原因是只要函数内部出现：`count = ···`，py就会默认认为`count`是这个函数自己的局部变量，但执行右边的`count+1`时，这个局部变量还没有值，所以报错。

这个时候加上`nonlocal count`，就是告诉py，这里的`count`不是内层函数自己的变量，而是外层函数里的那个`count`。

```py
def create_counter():
    count = 0

    def counter():
        nonlocal count
        count += 1
        return count

    return counter
```

#### 为什么每个闭包能保存自己的数据

仍然以上面的例子举例：

```py
def create_counter():
    count = 0

    def counter():
        nonlocal count
        count += 1
        return count

    return counter
```
假如此时分别创建两个计数器：

```py
counter1 = create_counter()
counter2 = create_counter()

print(counter1())
print(counter1())
print(counter2())
print(counter1())
print(counter2())
# 输出：
# 1
# 2
# 1
# 3
# 2
```

因为每调用一次`create_counter()`都会创建一套新的环境，和使用类创建多个对象有点类似，每个对象拥有自己的属性，而闭包则是每个函数拥有自己记住的外层变量。

#### 闭包的延迟绑定陷阱

```py
functions = []

for i in range(3):
    functions.append(lambda: i)

print(functions[0]())
print(functions[1]())
print(functions[2]())
```

输出不是012，而是222。

因为这些lambda记住的不是创建函数那一刻i当前的具体值，而是变量i本身，是对变量i的引用。

延迟绑定可以理解为：

>函数不是在创建时马上把i的值抄下来，而是在真正执行时再去查i现在是多少。

解决方法：利用默认参数：

```py
functions = []

for i in range(3):
    functions.append(lambda i=i: i)
```
使用默认参数来保存每次创建函数时变量i的值。

### 4. 装饰器

装饰器适合用来处理当多个函数都需要添加某个公共功能的情况，这样就不用在每个函数里重复写相同代码。

#### 基本语法
创建一个装饰器：

```py
def decorator(func):
    def wrapper(*args, **kwargs):
        # 调用前逻辑
        ...
        result = func(*args, **kwargs)

        # 调用后逻辑
        ...
        return result

    return wrapper
```
注意到最后返回的是`wrapper`而不是`wrapper()`。装饰完成后，外部的原函数名会重新指向`wrapper`，而`wrapper`中的`func`仍然指向原函数。

装饰器的核心公式：

```py
原函数 = 装饰器(原函数)
```

比如说下面这个timer函数，就是一个装饰器。

```py
import time

def timer(func):
    """一个计时装饰器，测量函数的执行时间"""
    # wrapper 用 *args, **kwargs 接收所有参数
    # 再原样传给原函数，这样不管原函数有几个参数都能通用
    def wrapper(*args, **kwargs):
        start = time.perf_counter()  # 记录开始时间
        # 调用原函数
        result = func(*args, **kwargs)
        end = time.perf_counter()  # 记录原函数执行结束时的计时值
        # 每个函数都有 __name__ 属性，记录了函数的名字
        print(f"{func.__name__} 执行耗时：{end - start:.4f} 秒")
        return result
    return wrapper

# 手动使用装饰器：用 timer 包装 slow_add
def slow_add(a, b):
    # time.sleep(0.1) 暂停 0.1 秒，模拟耗时操作
    time.sleep(0.1)
    return a + b

# 把 slow_add 传给 timer，得到包装后的版本
slow_add = timer(slow_add)

# 调用的是 wrapper，它会先计时，再调用原函数，再打印耗时
result = slow_add(1, 2)
# 输出类似：slow_add 执行耗时：0.10xx 秒
# 输出：结果：3
print(f"结果：{result}")
```

timer接收一个函数func，返回一个新函数wrapper，wrapper在调用func前后加了计时逻辑，最后slow_add = timer(slow_add)把原函数替换成包装后的版本。

#### `@` 语法糖

```py
import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} 执行耗时：{end - start:.4f} 秒")
        return result
    return wrapper

# 用 @ 语法糖，等价于 slow_add = timer(slow_add)
@timer
def slow_add(a, b):
    time.sleep(0.1)
    return a + b

@timer
def slow_multiply(a, b):
    time.sleep(0.2)
    return a * b

# 输出类似：slow_add 执行耗时：0.10xx 秒
r1 = slow_add(1, 2)
# 输出：3
print(r1)

# 输出类似：slow_multiply 执行耗时：0.20xx 秒
r2 = slow_multiply(3, 4)
# 输出：12
print(r2)
```

@timer写在函数定义上方，py在定义函数后自动执行`slow_add = timer(slow_add)`

#### 为什么装饰器需要嵌套函数

如果直接写：

```py
def timer(func):
    start = time.perf_counter()
    result = func()
    end = time.perf_counter()
    print(end - start)
    return result
```
的话，这样在执行`timer(slow_add)`的时候，就会立即调用原函数。

我们真正需要的是，`timer(slow_add)`先生成一个新函数，等以后调用这个新函数时，再执行计时逻辑。所以需要分成两个阶段：

```text
装饰阶段：
slow_add = timer(slow_add)
生成 wrapper，但不执行原函数

调用阶段：
slow_add(1, 2)
执行 wrapper，再由 wrapper 调用原函数
```
装饰器实际上运用了闭包，此处的闭包为：`闭包 = wrapper函数 + 它记住的原函数func`，而此处的func指向原来的slow_add。

#### `functools.wraps`

装饰器有个小问题：包装之后，原函数的名字和文档字符串会丢失。

```py
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def hello():
    """这是 hello 函数的文档"""
    print("Hello!")

# 原函数的名字和文档丢失了
# 输出：wrapper（应该是 hello）
print(hello.__name__)
# 输出：None（应该是文档字符串）
print(hello.__doc__)
```

因为hello实际上已经被替换成了wrapper，所以__name__和__doc__都是wrapper的，这在调试的时候会造成误解。

解决方法是用functools.wraps装饰wrapper：

```py
import functools

def my_decorator(func):
    # 加上这一行就够了
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def hello():
    """这是hello函数的文档"""
    print("Hello!")

print(hello.__name__)
print(hello.__doc__)
# 输出：hello
# 输出：这是hello函数的文档
```
写装饰器时在wrapper上方加上这行，就能把原函数的__name__、__doc__等属性复制过来。

#### 常用装饰器

1. `@functools.cache`（Python 3.9+）：无限制记忆化
    会缓存函数的返回值，相同的参数只计算一次。刷算法题做记忆化搜索时，如果不需要限制缓存大小，写起来最直接。
2. `@functools.lru_cache`：带LRU策略的缓存
    可以通过`maxsize`限制缓存大小；`@functools.lru_cache(maxsize=None)`的效果与`@functools.cache`类似。
3. `@staticmethod 和 @classmethod`：
   这两个用在类里面，调整方法和类的关系。

#### 带参数的装饰器

如果你想让装饰器本身也能传参数，那么需要再套一层函数：

```py
def 装饰器工厂(装饰器参数):
    def 装饰器(原函数):
        def 包装函数(*args, **kwargs):
            ...
            return 原函数(*args, **kwargs)

        return 包装函数

    return 装饰器
```
例如：

```py
from functools import wraps

def repeat(n):
    """让被装饰的函数重复执行n次"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def say_hello(name):
    print(f"你好，{name}!")

# say_hello会被执行3次
say_hello("Alice")
```

整个过程实际上分为两步：

1. `decorator = repeat(3)`
2. `say_hello = decorator(say_hello)`

即：

```text
repeat(times)
│
├── 接收装饰器自己的参数 times
│
└── decorator(func)
    │
    ├── 接收被装饰函数
    │
    └── wrapper(*args, **kwargs)
        └── 每次函数调用时真正执行
```

最外层接收装饰器的参数，中间层接收被装饰的函数，最内层是实际执行的包装函数。


#### 多个装饰器的执行顺序

```py
@decorator_a
@decorator_b
def func():
    pass
```

等价于：

```py
func = decorator_a(decorator_b(func))
```
调用时表现为从外向内：

```text
进入 decorator_a 的 wrapper
    ↓
进入 decorator_b 的 wrapper
    ↓
执行原函数
    ↓
退出 decorator_b
    ↓
退出 decorator_a
```

```py
from functools import wraps


def outer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("outer 开始")
        result = func(*args, **kwargs)
        print("outer 结束")
        return result

    return wrapper


def inner(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("inner 开始")
        result = func(*args, **kwargs)
        print("inner 结束")
        return result

    return wrapper


@outer
@inner
def work():
    print("执行 work")
```
最后输出：

```text
outer 开始
inner 开始
执行 work
inner 结束
outer 结束
```

#### 小结

>函数装饰器通常利用闭包保存被装饰的原函数。装饰时只创建并返回包装函数，不立即调用原函数；等以后调用包装后的函数时，包装函数才通过闭包中保存的 func 调用原函数。这属于延迟执行。

## 六、迭代器与生成器

### 1. 可迭代对象与迭代器

可迭代对象是能够传给`iter()`并获得迭代器的对象，例如列表、元组、字符串和range。

迭代器是能够通过`next()`依次取值的对象；迭代器本身也是可迭代对象，`iter(iterator)`通常会返回它自己。

#### 迭代器只能依次消费

>迭代器内部会记录“当前走到哪里了”。每取出一个元素，位置就向后移动一步；已经取出的元素通常不能回退，全部取完后，迭代器就耗尽了。

即迭代器已经把这个元素取出来了，并把当前位置向后移动了。

“消费”指的是消耗迭代器中的遍历进度，原对象中的原始数据并没有被改变。

#### for 循环也在消费迭代器

for循环的底层逻辑大概是：

```py
iterator = iter(z)

while True:
    try:
        item = next(iterator)
        print(item)
    except StopIteration:
        break
```
也就是说，for 循环也会不断调用 next()。

#### `list()`、`map()` 和 `filter()` 的消费时机
比如：

list(z)不是查看一下z，而是不断调用`next(z)`，直到取完为止，近似相当于：

```py
result = []

while True:
    try:
        item = next(z)
        result.append(item)
    except StopIteration:
        break
```

因此这会造成，两次`print(list(z))`之后，第二次打印出来的是空列表。

`map()`和`filter()`本身返回惰性迭代器，创建它们时通常不会立刻取完输入；当它们被`next()`、`for`或`list()`继续迭代时，才会逐步消费输入迭代器。

#### 为什么 `zip()` 不直接返回列表？

因为返回迭代器有一个很大的优点：不需要一开始就把所有结果全部存进内存，而是需要一个时才生成一个。

这种方法也叫**惰性计算**，也就是用到时再计算。优点是节省内存，适合大量数据，代价是它一般只能向前走，不能随意回退。


### 2. 生成器

生成器是py中一种按需产生数据的迭代器，每次需要一个值时，才计算并返回一个值；下次继续从上次暂停的位置运行。即**惰性计算**。

可以把生成器理解成：

>一个“可以暂停，可以继续执行，并且每次只吐出一个值”的函数执行过程。

例如：

```py
def generate():
    yield 1
    yield 2
    yield 3
```

此时`generate`是一个生成器函数，而`g = generate()`得到的是一个生成器对象。

#### 调用生成器函数时，函数体不会立即执行

```py
def generate():
    print("函数开始")
    yield 10
    print("继续执行")
    yield 20
    print("函数结束")


g = generate()

print("创建完毕")
```

此时输出只会有`创建完毕`。而：

```py
g = generate()
```

仅仅是在创建一个生成器对象。如果这时候加入：

```py
x = next(g)
print(x)
```

此时py才会真正开始执行generate函数，在`yield 10`执行完之后暂停。第二次再调用`next()`的时候，才会继续执行`yield 10`后面的代码。

#### 为什么for循环可以直接遍历生成器？


例如：

```py
def generate():
    yield 10
    yield 20
    yield 30


for x in generate():
    print(x)
```

结果为10 20 30.

因为前面说过for循环本质上大概就是不停地`next()`，直到生成器耗尽：

```py
iterator = iter(generate())

while True:
    try:
        x = next(iterator)
        print(x)
    except StopIteration:
        break
```

#### 生成器的主要创建方法

1. 生成器表达式
2. 带有yield的生成器函数


#### 生成器表达式

比如：

```py
number = [x * x for x in range(1_000_000)]
```
这是列表推导式，它会计算0到100万-1的平方，然后把100万个结果全部存起来。

而把[]换成()就是生成器表达式：

```py
numbers = (x * x for x in range(1_000_000))
```

只有逐步执行`next(numbers)`的时候，才会逐步计算从0到100万-1的平方。




## 七、推导式

### 1. 列表推导式的基本语法
```py
[表达式 for 变量 in 可迭代对象]
```
可以理解为：

>从“可迭代对象”中依次取出每个元素，交给“变量”，计算“表达式”，然后把每次计算的结果放进新列表。

若变量在前面的表达式中未使用到，那么可以理解为：可迭代对象每产生一个元素，就把前面的`表达式`计算一次。执行次数由可迭代对象中的元素数量决定。

### 2. 条件筛选与条件表达式
带筛选条件：

- if放在后面：筛选元素
```py
[表达式 for 变量 in 可迭代对象 if 条件]
```
- if-else放在前面：将符合条件的元素转换为相应结果
```py
[结果1 if 条件 else 结果2 for 变量 in 可迭代对象]
```

### 3. 在列表推导式中调用函数
可以在表达式部分调用函数，例如：

```py
def square(x):
    return x * x

result = [square(i) for i in range(5)]
```

### 4. 二维列表的共享引用陷阱
创建二维列表千万不能用 `[[0]*4]*3`。因为 `*3` 复制的是引用，三行指向的是同一个列表对象，修改一行其他行也会跟着变。用列表推导式 `[[0]*cols for _ in range(rows)]` 才是正确做法，每行都是独立的列表对象。

例如：

```py
grid = [[0] * 4] * 3

grid[0][1] = 5

print(grid)
```
输出：

`[[0, 5, 0, 0],

 [0, 5, 0, 0],

 [0, 5, 0, 0]]`


### 5. 集合推导式与字典推导式

集合推导式：

```py
squares = {x * x for x in range(5)}
print(squares)
```

字典推导式：

```py
squares = {x: x * x for x in range(5)}
print(squares)
```

也可以配合条件：

```py
even_squares = {
    x: x * x
    for x in range(10)
    if x % 2 == 0
}
```

列表、集合、字典推导式适合表达简单的“遍历 + 转换/筛选”。如果逻辑已经包含很多层条件、异常处理或副作用，通常改用普通`for`循环会更清晰。

### 6. 推导式中的作用域

Python 3中，推导式内部的循环变量拥有自己的局部作用域，不会直接泄漏到外层：

```py
x = 100
nums = [x * 2 for x in range(3)]

print(x)     # 100
print(nums)  # [0, 2, 4]
```

## 八、常用内置函数与数学工具

### 1. `range()`
生成一个整数范围，常用于for循环，包含范围为**前闭后开**

```py
range(stop)
range(start, stop)
range(start, stop, step)
```
- 返回值：返回一个range对象
- 步长step不能为0

### 2. `enumerate()`

同时获得下标和元素

#### 基本语法

```py
enumerate(iterable, start=0)
```
参数：

- iterable：需要遍历的可迭代对象
- start：编号从哪个数字开始，默认从 0 开始

返回值：

- 一个enumerate迭代器对象
- 遍历时，每次产生一个`(编号，元素)`元组


### 3. `zip()`

#### 基本用法

`zip()` 是 Python 中用来把多个可迭代对象中相同位置的元素配对组合的函数。

最常见的场景是：同时遍历两个或多个列表。可以把它理解成把两个列表“拉上拉链”。


```text
["小明", "小红", "小刚"]
   ↓       ↓       ↓
[  90,     85,      92 ]

组合后：

[("小明", 90), ("小红", 85), ("小刚", 92)]
```
**注：**

- `zip()`返回的是一个**迭代器对象**
- 可以组合不同类型的可迭代对象


#### 配合 `for` 循环使用

```py
names = ["小明", "小红", "小刚"]
scores = [90, 85, 92]

for name, score in zip(names, scores):
    print(name, score)
```

#### 同时组合三个或更多可迭代对象

```py
names = ["小明", "小红", "小刚"]
scores = [90, 85, 92]
ages = [18, 19, 18]

result = list(zip(names, scores, ages))

print(result)
```

#### 可迭代对象长度不同时

`zip()`会以最短的可迭代对象为准

#### 解压操作

例如：

```text
students = [
    ("小明", 90),
    ("小红", 85),
    ("小刚", 92)
]

names, scores = zip(*students)

print(names)
print(scores)

得到：
("小明", "小红", "小刚")
(90, 85, 92)
```

通过这一解压操作还能用于实现**矩阵转置**：

```text
matrix = [
    [1, 2, 3],
    [4, 5, 6]
]

result = list(zip(*matrix))

print(result)

得到：
[(1, 4), (2, 5), (3, 6)]
```
若想让结果仍为二维列表：

```text
result = [list(row) for row in zip(*matrix)]

print(result)

得到：
[
    [1, 4],
    [2, 5],
    [3, 6]
]
```

### 4. `map()`

将指定函数依次应用于可迭代对象中的每一个元素

#### 基本语法

```py
map(function, iterable)
```
返回值：一个map迭代器对象

#### 可处理多个可迭代对象

```py
map(function, iterable1, iterable2, ...)
```

例如：

```py
numbers1 = [1, 2, 3]
numbers2 = [10, 20, 30]

result = map(lambda x, y: x + y, numbers1, numbers2)

print(list(result))
```

若多个可迭代对象长度不同，map()会在最短的可迭代对象结束时停止。

#### 示例

`map(int, str(n))`会依次把字符串中的每个字符转换为整数。

```py
n = 124

str(n)                    # "124"
map(int, str(n))          # 依次产生 1、2、4
sorted(..., reverse=True) # [4, 2, 1]
```


### 5. `filter()`

对每个元素进行条件判断，只保留判断结果为真的元素。

#### 基本语法

```py
filter(function, iterable)
```
判断函数function应该接受一个元素，并返回一个布尔值，但判断函数返回的也不一定非得是布尔值，因为py会根据一个值的“真假”判断是否保留元素，常见假值包括：

```py
False
None
0
0.0
""
[]
{}
set()
```
其他大多数值都是真值。

**注：**`filter()`的第一个参数还可以直接写成None，此时会自动删除所有假值。


### 6. `sorted()`

对可迭代对象进行排序，返回一个新的列表

```py
sorted(iterable, key=None, reverse=False)
```
- 参数：key为指定排序依据，reverse为是否降序，默认`False`表示升序
- 返回值：返回一个新的**列表**

注：`sorted()`与列表的`.sort()`不同，后者会修改原列表，且返回`None`。


### 7. `reversed()`

反向遍历一个序列，不会修改原序列

```py
reversed(sequence)
```

- 参数：sequence为列表、元组、字符串、range等可逆序对象
- 返回值：返回一个反向迭代器


### 8. `round()`

对数字进行舍入

```py
round(number, ndigits=None)
```

- 参数：number为需要舍入的数字，ndigits为保留的小数位数，省略时取整
- 返回值：返回舍入后的数字

### 9. `divmod()`

同时计算整除的商和余数

```py
divmod(a, b)
```

- 参数：a为被除数，b为除数
- 返回值：返回一个二元组`(商，余数)`

### 10. `ord()`
把单个Unicode字符转换为对应的整数码点

### 11. `chr()`
把整数码点转换为对应的Unicode字符

```py
# 经典用法：用数组统计字母频率
text = "abracadabra"
freq = [0] * 26
for ch in text:
    freq[ord(ch) - ord('a')] += 1

# 输出每个出现过的字母及其频率
for i in range(26):
    if freq[i] > 0:
        print(f"{chr(i + ord('a'))}: {freq[i]}", end="  ")
# 输出：a: 5  b: 2  c: 1  d: 1  r: 2
print()
```
`ord(ch) - ord('a')` 这个技巧把小写字母映射到 0~25，非常适合用数组代替哈希表来统计字母频率。刷题时很常用。


### 12. `max()`、`min()`

返回可迭代对象中的最值，或多个位置参数中的最值

#### 基本语法

```text
max(iterable, *, key=None, default=...)

或者：

max(arg1, arg2, *args, key=None)
```

参数：

- iterable：需要查找最大值的可迭代对象，例如列表、元组、集合等
- arg1, arg2, ...：也可以直接传入多个值进行比较
- key：指定比较规则，默认直接比较元素本身
- default：当 iterable 为空时返回的默认值

返回值：

- 返回最大的那个**原元素**
- 如果使用 key，根据 key(element) 的结果进行比较，但返回的仍然是**原元素**，例如：
```py
max([-10, 3, 5], key=abs)  # 返回-10
```

min()同理

### 13. `pow()`

进行幂运算

#### 基本语法

```text
普通幂：
pow(base, exp)

带模运算：
pow(base, exp, mod)
```

返回值：

- 带模运算：`base`^`exp` mod `mod`

#### 快速幂取模

```py
# pow(a, b, mod) 快速幂取模：计算 a^b % mod
# 这比先算 a**b 再取模快得多，不会产生超大中间值
# 刷题中经常遇到"答案对 10^9+7 取模"
MOD = 10**9 + 7
result = pow(2, 100, MOD)
print(f"2^100 mod (10^9+7) = {result}")

# 对比：直接用 ** 也能算，但数字太大时效率低
```

### 14. `math` 模块

```py
import math

# 开平方
print(f"sqrt(9) = {math.sqrt(9)}")
print(f"sqrt(2) = {math.sqrt(2):.4f}")

# 向上取整、向下取整
print(f"ceil(3.2) = {math.ceil(3.2)}")    # 4
print(f"floor(3.8) = {math.floor(3.8)}")  # 3

# 最大公约数
print(f"gcd(12, 8) = {math.gcd(12, 8)}")  # 4
# Python 3.9+ 支持多个参数
print(f"gcd(12, 8, 6) = {math.gcd(12, 8, 6)}")  # 2

# 对数
print(f"log2(8) = {math.log2(8)}")     # 3.0
print(f"log(e) = {math.log(math.e)}")  # 1.0
print(f"log10(1000) = {math.log10(1000)}")  # 3.0

# 无穷大常量
print(f"math.inf = {math.inf}")
print(f"5 < math.inf ? {5 < math.inf}")
```
**注：**

- python中表示无穷大还有另一种方式`float('inf')`，表示负无穷可以写成`float('-inf')`或`-math.inf`
- python中的整除`//`是向下取整


### 15. 进制转换相关函数

#### `bin()`

将整数转换为二进制**字符串**，不改变原数字

```py
bin(x)
```

例如：

```py
x = bin(42)

print(x)
print(type(x))

# 输出：
# 0b101010
# <class 'str'>
```

注：

1. `0b`是二进制前缀
2. 负数也可以，只不过返回的是带负号的字符串，不是计算机内部补码表示

#### `oct()`

将整数转换为八进制字符串

注：

1. `0o`表示八进制


#### `hex()`

将整数转换为十六进制字符串

注：

1. `0x`表示十六进制
2. 显示时默认显示小写字母


#### `int()`

创建或转换成整数

```py
int(x)

int(string, base)
```

参数：

- base：字符串当前使用的是几进制
  **注**：若`base=0`，则py会根据前缀自动判断进制

返回值：

- int整数

## 九、常用对象方法

### 1. `str.strip()`
删除字符串开头和结尾的空白字符或指定字符，即只删除两端，不删除中间。

```py
string.strip(chars=None)
```

- 参数：chars为要删除的字符集合，默认删除空格、换行、制表符等
- 返回值：返回处理后的新字符串
- 相关方法：
```py
text.lstrip()  # 只删除左侧
text.rstrip()  # 只删除右侧
```

### 2. `str.split()`
按照指定分隔符拆分字符串

```py
string.split(sep=None, maxsplit=-1)
```

- 参数：sep为分隔符，默认按照任意空白字符拆分；maxsplit为最多拆分多少次，默认全部拆分
- 返回值：返回一个字符串**列表**

### 3. `str.replace()`
将字符串中的指定内容替换成新内容

```py
string.replace(old, new, count=-1)
```

- 参数：old为要被替换的内容，new为替换后的内容，count为最多替换多少次，默认全部替换

### 4. `str.join()`
使用指定字符串，将多个字符串连接起来

```py
separator.join(iterable)
```
- 参数：separator为元素之间使用的连接符；iterable为包含字符串的可迭代对象
- 返回值：返回连接后的新字符串

### 5. `list.sort()`

#### 使用元组进行多级排序

元组在比较时会先比第一个元素，相等再比第二个，以此类推。对于数字字段，如果想让某一项**降序**，可以对这一项取负号

例如：

```py
students = [("Alice", 88), ("Bob", 95), ("Charlie", 88), ("Diana", 95)]
students.sort(key=lambda x: (-x[1], x[0]))
# 输出：[('Bob', 95), ('Diana', 95), ('Alice', 88), ('Charlie', 88)]
print(students)
```

### 6. `dict.get()`

根据键获取字典中的值；如果键不存在，不会报错，而是返回一个默认值。

```py
dict.get(key, default)
```

- 参数：key为要查找的键，必填；default为键不存在时返回的默认值，可选，默认是`None`
- 返回值：若键存在，返回该键对应的值；若键不存在，返回default，未传入default时返回None

#### 频率统计的经典写法

```py
freq[ch] = freq.get(ch, 0) + 1
```

## 十、异常处理

### 1. `try / except / else / finally` 完整结构

```python
try:
    # 尝试执行的代码
    result = 10 / 0
    
except ZeroDivisionError:
    # 捕获特定异常
    print("除数不能为零")
    
except (TypeError, ValueError) as e:
    # 捕获多种异常
    print(f"发生错误: {e}")
    
except Exception as e:
    # 捕获所有其他异常
    print(f"未知错误: {e}")
    
else:
    # 没有异常时执行
    print("计算成功!")
    
finally:
    # 无论是否异常都会执行
    print("这是最后执行的代码")
```

### 2. 常见异常类型

|异常类型|说明|示例|
|---|--|---|
|ZeroDivisionError	|除零错误	|1/0|
|TypeError	|类型错误	|'1' + 1|
|ValueError	|值错误	|int('abc')|
|IndexError|	索引错误|	[1][10]|
|KeyError|	键错误	|{}['key']|
|FileNotFoundError|	文件不存在|	open('nofile.txt')|


```text
BaseException
├── SystemExit
├── KeyboardInterrupt  
├── GeneratorExit
└── Exception  # ← 我们通常处理的异常
    ├── TypeError      # 类型错误
    ├── ValueError     # 值错误
    ├── KeyError       # 键错误
    ├── FileNotFoundError
    └── ... (其他所有异常)
```

### 3. 自定义异常
```py
# 定义自定义异常
class AgeError(Exception):
    """年龄异常类"""
    pass

class UnderAgeError(AgeError):
    """年龄太小异常"""
    pass

class OverAgeError(AgeError):
    """年龄太大异常"""
    pass

def check_age(age):
    if age < 0:
        raise AgeError("年龄不能为负数")
    elif age < 18:
        raise UnderAgeError("年龄太小，需要满18岁")
    elif age > 120:
        raise OverAgeError("年龄太大，超出范围")
    else:
        print(f"年龄 {age} 验证通过")

# 使用自定义异常
try:
    check_age(15)
except UnderAgeError as e:
    print(f"未成年: {e}")
except OverAgeError as e:
    print(f"超龄: {e}")
except AgeError as e:
    print(f"年龄错误: {e}")
```

## 十一、面向对象基础

面向对象的思路是：

>把一组相关的数据以及操作这些数据的函数，封装为一个整体

这个整体称为`对象`，对象所属的类型称为`类`

### 1. 类与对象

用`class`关键字定义一个类，类就是一个模版，定义了这类对象有什么`属性`(数据)和什么`方法`(操作)

```py
class Student:
    # __init__ 初始化已经创建好的对象，创建对象时自动调用
    # self 指向当前正在操作的那个对象本身，类似其他语言的 this
    def __init__(self, name, age):
        # 给对象绑定属性
        self.name = name
        self.age = age
        self.scores = []  # Python 不要求你提前声明对象有哪些属性，所以 scores 可以直接在赋值时创建。

    # 定义方法：添加成绩
    def add_score(self, score):
        self.scores.append(score)

    # 定义方法：计算平均分
    def average(self):
        if not self.scores:
            return 0
        return sum(self.scores) / len(self.scores)

# 创建对象（实例化）
alice = Student("Alice", 20)
bob = Student("Bob", 21)

# 调用方法
alice.add_score(90)
alice.add_score(85)
alice.add_score(92)

bob.add_score(78)
bob.add_score(88)

# 访问属性和调用方法
# 输出：Alice 的平均分：89.0
print(f"{alice.name} 的平均分：{alice.average()}")
# 输出：Bob 的平均分：83.0
print(f"{bob.name} 的平均分：{bob.average()}")
```

普通的py自定义类默认允许随时读取和修改属性，也可以动态添加新属性；但`__slots__`、property等机制可以对属性访问进行限制


#### 实例属性与类属性

##### a. 实例属性与类属性的区别

- 实例属性：通过`self.xxx`设置，每个实例都有独立的数据
- 类属性：通常用于所有实例共享的数据
```py
class Student:
    school = "BUPT"  # 类属性
    def __init__(self, name):
        self.name = name  # 实例属性
        self.scores = []
alice = Student("Alice")
bob = Student("Bob")

alice.scores.append(100)

print(alice.scores)  # [100]
print(bob.scores)    # []
print(Student.school)  # BUPT
print(alice.school)    # BUPT
print(bob.school)      # BUPT
```
实例变量通常用于保存每个对象各自独有的数据

##### b. 实例同名属性与类属性
```py
alice.school = "Alice 的学校"

print(alice.school)    # Alice 的学校
print(bob.school)      # BUPT
print(Student.school)  # BUPT
```
此处**并未修改**`Student.school`，而是给 alice 新增了一个同名实例属性。

属性查找大致是：

>先找 alice 自己的实例属性
        ↓
找不到再找 Student 类属性
        ↓
再找父类中的属性

**当实例属性与类属性同名时，实例属性优先**

##### c. 可变类属性的共享问题

类属性如果是列表、字典、集合等可变对象，会被实例共享。如果本来就需要所有实例共享，这样写没有问题；如果希望每个实例各自拥有一份，就应该放在`__init__`中。

```py
class Student:
    def __init__(self, name):
        self.name = name
        self.scores = []
    # 不能写成
    # scores = []
```

#### 属性访问与“封装”

1. 单下划线`_name`：
   表示这是内部属性，外部代码最好不要直接操作，但实际上仍可以访问。仅为约定，不是强制限制。
    ```py
    self._age = age
    ```
2. 双下划线`__name` ：
   双下划线主要是为了避免子类属性重名，不是安全机制，也不等于真正私有。

### 2. Python 中的三种方法

#### 实例方法

第一个参数是`self`，用于操作某个具体对象

适用场景：方法需要读取或修改实例属性

#### 类方法
使用`@classmethod`，第一个参数通常写成`cls`，表示当前类

```py
class Student:
    school = "BUPT"

    def __init__(self, name, age):
        self.name = name
        self.age = age

    @classmethod
    def from_text(cls, text):
        name, age = text.split(",")
        return cls(name, int(age))  # 此处就相当于通过给类名加括号来创建对象
```
调用：

```py
alice = Student.from_text("Alice,20")

print(alice.name)  # Alice
print(alice.age)   # 20
```

整个过程详细解释：

1. 因为 from_text 被 @classmethod 修饰，Python 会自动把 Student 类传给第一个参数 cls。所以这里的cls本质上就是Student，即
    ```py
    cls = Student
    text = "Alice, 20"
    ```
2. 然后拆分字符串，转换年龄类型
3. 接着创建对象，`return cls(name, int(age))`等价于`return Student("Alice", 20)`，这会自动调用`Student.__init__(新对象, "Alice", 20)`
4. 最终得到：
    ```py
    student.name  # "Alice"
    student.age   # 20
    ```

##### a. 为什么不直接写 `return Student(name, int(age))`

使用cls的核心优势是：

>谁调用这个类方法，就创建谁的对象

#### 静态方法

使用`@staticmethod`，不会自动接收 self 或 cls。

```py
class Student:
    @staticmethod
    def is_valid_score(score):
        return 0 <= score <= 100
```
调用：

```py
print(Student.is_valid_score(90))   # True
print(Student.is_valid_score(120))  # False
```
它本质上更像一个普通函数，只是逻辑上和Student类关系密切，所以放在类里面。


### 3. 继承与 `super()`

#### 基础继承

继承就是在已有类的基础上扩展。子类可以按照属性查找规则使用父类中可继承的属性和方法，还可以添加新的或者重写已有的。

```py
# 父类
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "..."

# 子类：括号里写父类名
class Cat(Animal):
    def speak(self):
        return "喵~"

class Dog(Animal):
    def speak(self):
        return "汪！"

# 子类自动拥有父类的 __init__，所以可以传 name
cat = Cat("小花")
dog = Dog("旺财")

# 输出：小花 说：喵~
print(f"{cat.name} 说：{cat.speak()}")
# 输出：旺财 说：汪！
print(f"{dog.name} 说：{dog.speak()}")
```

1. Cat(Animal) 表示 Cat 继承自 Animal。Cat 没有定义 `__init__`，所以自动用 Animal 的。
2. Cat 重写了 speak() 方法，调用时会用 Cat 自己的版本。

#### 扩展 `__init__`

如果子类需要在父类的基础上扩展 `__init__`，可以用 super() 调用父类的方法：

```py
class Animal:
    def __init__(self, name):
        self.name = name

    def info(self):
        return f"名字：{self.name}"

class Pet(Animal):
    def __init__(self, name, owner):
        # 先调用父类的 __init__，设置 name
        super().__init__(name)
        # 再设置子类特有的属性
        self.owner = owner

    # 重写 info 方法，在父类基础上扩展
    def info(self):
        # 调用父类的 info 方法
        base_info = super().info()
        return f"{base_info}，主人：{self.owner}"

pet = Pet("小白", "张三")
# 输出：名字：小白，主人：张三
print(pet.info())
```

super() 返回一个代理对象，通过它可以按照方法解析顺序MRO继续查找方法。在这个单继承例子中，`super().__init__(name)` 就是调用父类 Animal 的 `__init__`，确保 name 属性被正确设置，然后子类再添加自己的 owner 属性。

### 4. 魔术方法

以双下划线开头和结尾的特殊方法，由py在特定场景下自动调用

#### `__call__()` 与类装饰器

对象实现`__call__()`后，对象本身就可以像函数一样使用。

```py
class Timer:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        print("开始执行")
        result = self.func(*args, **kwargs)
        print("执行结束")
        return result
```

使用：

```py
@Timer
def slow_add(a, b):
    return a + b
```

这里没有使用函数闭包，而是把原函数保存在`self.func`里面。

**注：** 这个例子主要用于理解`__call__()`和类装饰器的基本原理。实际工程中的通用类装饰器还可能需要考虑函数元数据、实例方法绑定等问题。


### 5. `@property`

普通属性可以直接读取和修改：

```py
class User:
    def __init__(self, age):
        self.age = age
```

如果以后希望在读取或修改属性时加入校验逻辑，可以使用`property`，同时仍然保持`obj.age`这样的访问形式：

```py
class User:
    def __init__(self, age):
        self.age = age

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if value < 0:
            raise ValueError("年龄不能为负数")
        self._age = value


user = User(20)
print(user.age)
user.age = 21
```

这里真正保存数据的是`_age`，而`age`对外表现得仍像普通属性。

注意：不要为了“面向对象”就把所有属性都机械地写成property。只有在确实需要校验、计算或兼容旧接口时再使用。

### 6. `dataclass`

当一个类主要用于保存数据时，手写大量`__init__`、`__repr__`、`__eq__`通常很重复，可以使用`@dataclass`。

dataclass不是说这个类只能用来存数据，它仍然是一个正常的py类，只不过`@dataclass`会帮你自动生成一些特别常见的样板代码。

`@dataclass`是一个类装饰器，专门帮“主要用来存数据的类”自动生成`__init__/__repr__、__eq__`等重复代码：

```py
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int


user = User("Alice", 20)
print(user)  # User(name='Alice', age=20)
```

带默认值：

```py
@dataclass
class Config:
    host: str = "localhost"
    port: int = 8000
```
但注意，**有默认值的字段必须放后面。**

这里的：

```py
name:str
age_int
```

会被`dataclass`看作字段，然后自动生成`__init__(self, name, age)`。

而`name:str`是py的**类型注解**，py的普通类型注解默认不会强制进行运行时类型检查。

类型注解主要用于：

- 阅读代码
- IDE提示
- 静态类型检查器
- `dataclass`判断哪些名称属于字段

#### `__repr__()`

这个魔术方法和`__str__()`坐一桌，用来规定一个对象应该以什么字符串形式表示出来。比如普通类如果没有专门定义对象的字符串表示，通常就会看到类似这样的输出：

```py
class Student:
    def __init__(self, name, age):
        self.name = name
        self.age = age


s = Student("小明", 18)

print(s)

#输出：<__main__.Student object at 0x000001...>
```

如果此时定义`__repr__()`：

```py
class Student:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"Student(name={self.name!r}, age={self.age!r})"

#输出：Student(name='小明', age=18)
```

##### 基本语法

```py
def __repr__(self):
    return "表示这个对象的字符串"
```

`__repr__()`必须返回字符串str。

可以用`print(repr(s))`或者在交互解释器里直接输入`s`来触发，使用`repr`来表示对象。

`!r`表示使用这个值的`repr()`结果，例如：

```py
name = "小明"

print(f"{name}")
print(f"{name!r}")

# 输出：
# 小明
# '小明'
```

`__repr__()`通常是给程序员，调试器看的对象表示，所以一般希望它信息明确，能看出对象类型，能看出重要属性，如果方便，尽量长得像创建这个对象的代码。


#### `__eq__()`

这个方法用来规定：两个对象使用`==`比较时，什么情况下认为它们相等。

例如：

```py
class Student:
    def __init__(self, name, age):
        self.name = name
        self.age = age


s1 = Student("小明", 18)
s2 = Student("小明", 18)

print(s1 == s2)

#结果通常都是False
```
虽然`s1.name == s2.name s1.age == s2.age`都是True，但是s1和s2指向的仍然是两个不同的Student对象，如果没有自定义适当的`__eq__()`，py不会自动认为属性一样就是相等的。

例如此时我们可以规定，姓名和年龄都相同，就认为两个学生是相等的：

```py
class Student:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __eq__(self, other):
        if not isinstance(other, Student):
            return NotImplemented
        
        return (self.name == other.name
        and self.age == other.age)

s1 = Student("小明", 18)
s2 = Student("小明", 18)
s3 = Student("小红", 18)

print(s1 == s2)
print(s1 == s3)

# 输出：
# True
# False
```

#####


#### 列表默认值不能直接写`[]`

可变默认值不能直接写成`[]`或`{}`，应该使用`default_factory`：

```py
from dataclasses import dataclass, field

@dataclass
class Student:
    name: str
    scores: list = field(default_factory=list)
```
这里的：

```py
field(default_factory=list)
```

表示：每创建一个`Student`对象，都重新调用一次`list()`，产生一个新的空列表。

这和普通函数的“可变默认参数”陷阱本质上类似：不应该让多个实例意外共享同一个可变对象。

`field()`用于对某个dataclass字段进行更加详细的配置。

####  `__post_init__`

有时候仅靠自动生成的`__init__`不够，还想再初始化后执行一些额外逻辑时，可以使用`__post_init__`。

```py
@dataclass
class Student:
    name:str
    age:int

    def __post_init__(self):
        if self.age < 0:
            raise ValueError("年龄不能小于0")
```

执行`Student("小明"， -1)`就会报错，此时的执行顺序可以理解为：

```py
Student("小明", 18)
        ↓
自动生成的 __init__
        ↓
self.name = "小明"
self.age = 18
        ↓
自动调用 __post_init__()
```

在`__post_init__`中是可以创建计算属性的，例如：

```py
@dataclass
class Rectangle:
    width:float
    height:float

    def __post_init__(self):
        self.area = self.width * self.height

r = Rectangle(10, 20)
print(r.area)
#输出：200
```

#### `@dataclass`的主要参数

常见写法：

```py
@dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    frozen=False,
    slots=False
)
class Student:
    ...
```

##### a.order参数：是否生成大小比较方法

默认dataclass支持`==, !=`，但不自动支持`<, >, <=, >=`，如果把order参数设置为True，那么就可以让对象按照字段定义顺序进行比较。比如：

```py
@dataclass(order=True)
class Student:
    score: int
    name: str

s1 = Student(80, "小明")
s2 = Student(90, "小红")

print(s1 < s2)
#输出：True
```
这里就是先比较score，如果相同，就会继续比较name，以此类推。

##### b.frozen参数：是否禁止正常修改字段

这个参数可以创建近似不可变的数据类：

```py
@dataclass(frozen = True)
class Point:
    x:int
    y:int

p = Point(1, 2)
print(p.x)
```

但如果`p.x = 100`的话，就会报错，因此可以理解成创建出来之后，不允许正常地重新修改字段，适合以下字段：

- 坐标
- 配置
- 不可变记录
- 值对象

##### c.slots参数：是否使用slots

现代py中还会经常看到：

```py
@dataclass(slots=True)
class Student:
    name:str
    age:int
```

这会使用`__slots__`机制，可以简单理解为**限制对象主要只能拥有预先声明好的字段，并可能减少大量对象的内存开销。**



### 3. `__slots__`（了解）

普通自定义类实例通常有`__dict__`，因此可以动态添加属性：

```py
class User:
    pass

user = User()
user.name = "Alice"
```

某些场景可以使用`__slots__`限制实例允许拥有的属性，并减少大量实例的部分内存开销：

```py
class Point:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y
```

一般业务代码不用为了“优化”主动到处使用`__slots__`，知道它改变了实例属性存储方式即可。



## 十二、模块、包与依赖管理

### 1. 模块与 `import`

一个`.py`文件通常就是一个模块。

假设：

```text
project/
├── main.py
└── math_utils.py
```

`math_utils.py`：

```py
def add(a, b):
    return a + b
```

`main.py`：

```py
import math_utils

print(math_utils.add(1, 2))
```

也可以只导入某个名字：

```py
from math_utils import add

print(add(1, 2))
```

可以起别名：

```py
import numpy as np
```

不推荐：

```py
from math_utils import *
```

因为这会让当前命名空间中突然出现很多名字，难以判断一个变量或函数从哪里来。

### 2. `__name__` 与程序入口

每个模块都有`__name__`变量。

当文件被直接运行时：

```py
__name__ == "__main__"
```

当它被其他模块导入时，`__name__`通常是模块名。

因此常见写法：

```py
def main():
    print("程序开始")


if __name__ == "__main__":
    main()
```

这样导入这个模块时不会自动执行`main()`中的程序入口逻辑。

### 3. 包与 `__init__.py`

多个模块可以组成一个包：

```text
project/
├── main.py
└── app/
    ├── __init__.py
    ├── service.py
    └── utils.py
```

例如：

```py
from app.service import run
```

现代Python支持namespace package，因此某些场景没有`__init__.py`也能形成包；但普通项目中保留`__init__.py`仍然很常见，而且可以明确表达这个目录是Python包。

### 4. 绝对导入与相对导入

绝对导入：

```py
from app.utils import parse_data
```

包内部也可以使用相对导入：

```py
from .utils import parse_data
from ..config import settings
```

`.`表示当前包，`..`表示上一级包。

实际工程中通常更推荐清晰的绝对导入；相对导入适合包内部关系明确的场景。

### 5. 虚拟环境与依赖

不同项目可能依赖不同版本的第三方库，因此一般不要把所有库都装到同一个全局Python环境中。

使用`venv`：

```bash
python -m venv .venv
```

Windows PowerShell中激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
python -m pip install fastapi
```

查看依赖：

```bash
python -m pip freeze
```

现代项目还经常使用`pyproject.toml`统一保存项目元数据、构建配置和工具配置，并使用`uv`等工具管理环境和依赖。第一次学习时先理解“项目环境彼此隔离”这个核心概念即可。

## 十三、类型标注 `typing`

类型标注本质上是给程序员、IDE、类型检查器、框架看的“类型说明”，

### 1. 基本类型标注

Python是动态类型语言，类型标注不会把它变成静态类型语言；它主要用于：

- 提高可读性
- IDE自动补全
- 静态类型检查
- 框架根据类型生成校验或Schema

例如：

```py
def add(a: int, b: int) -> int:
    return a + b
```

变量也可以标注：

```py
name: str = "Alice"
age: int = 20
```

### 2. 容器类型

Python 3.9+通常可以直接使用内置泛型：

```py
names: list[str] = ["Alice", "Bob"]
scores: dict[str, int] = {"Alice": 90}
point: tuple[int, int] = (10, 20)
tags: set[str] = {"python", "agent"}
```

`list[str]`说明这是一个“元素应该是字符串”的列表，其余类型同理。

### 3. 联合类型与可空值

Python 3.10+可以使用`|`表示**联合类型**，比如说此处的value，就是既可以是int，也可以是str：

```py
def normalize(value: int | str) -> str:
    return str(value)
```

可能为`None`：

```py
def find_user(user_id: int) -> str | None:
    if user_id == 1:
        return "Alice"

    return None
```

所以此处调用`find_user`之后，不能想当然地认为返回就一定是str，还要考虑返回值为None时代码应该如何处理。

旧代码里还会看到：

```py
from typing import Optional, Union

Optional[str]       # 等价于 str | None
Union[int, str]     # 等价于 int | str
```

### 4. `Any` 与 `object`

`Any`基本相当于告诉类型检查器：“这里暂时不要检查”：

```py
from typing import Any

def handle(value: Any) -> Any:
    return value.foo.bar()
```

但不要无脑把所有复杂类型都写成`Any`，否则类型标注的价值会被抵消。

`object`则表示“可以接收任何Python对象”，但读取具体属性前仍然需要缩窄类型，因为`object`并没有告诉类型检查器这个对象具体有哪些能力。

### 5. `Callable` 与 `Awaitable`

函作为参数传递的时候也可以进行类型标注：

```py
from collections.abc import Callable

def apply_twice(func: Callable[[int], int], value: int) -> int:
    return func(func(value))
```

```text
Callable[
    [int],   ← 参数列表
    int      ← 返回值
]
```
意思就是`func`必须是一个接收一个int，返回一个int的可调用对象。

异步回调中还可能看到：

```py
from collections.abc import Awaitable, Callable

AsyncHandler = Callable[[str], Awaitable[str]]
```

其中，`Callable[[str], Awaitable[str]]`表示接收一个str，返回一个可以被`await`的对象，并且最终得到`str`。

所以这里的`AsyncHandler`大致描述一个异步处理函数，输入字符串，最终异步得到字符串。

这类类型在Agent工具、回调、Middleware和异步SDK中很常见。

### 6. `TypedDict`：给字典定义Schema

普通字典中不同键可以有不同的值类型，比如说：

```py
user = {
    "name": "Alice",
    "age": 20
}
```

类型标注如果只写`dict`，或者`dict[str, object]`的话，信息太少，而`TypedDict`可以描述这种固定结构：

```py
from typing import TypedDict

class UserData(TypedDict):
    name: str
    age: int


def greet(user: UserData) -> str:
    return f"你好，{user['name']}"
```

注意：运行时它仍然只是普通`dict`，`TypedDict`主要服务于静态类型检查。

### 7. `Protocol`：Python的接口

`Protocol`用于描述“只要拥有这些方法/属性就算满足要求”的结构化接口：

```py
from typing import Protocol

class Reader(Protocol):
    def read(self) -> str:
        ...


def load(reader: Reader) -> str:
    return reader.read()
```

即：一个对象只要拥有符合要求的`read() ->str`方法，我就可以把它当作`Reader`。

此时我们定义：

```py
class FileReader:
    def read(self) -> str:
        return "文件内容"
```

注意到并不是`class FileReader(Reader)`，但`load(FileReader())`从静态类型角度照样可以成立。因为`FileReader`刚好满足`Reader`的`def read(self) -> str:`要求，这就是所谓的**结构化类型**。

调用`load()`的对象不一定需要显式继承`Reader`，只要它拥有兼容的`read()`方法，就可以通过静态类型检查。

这种方式和py的“鸭子类型”很契合：我不管你是不是“鸭子类”；你会鸭子叫、会鸭子走，我就把你当鸭子。

### 8. `TypeVar` 与 `Generic`（了解后会用）

当输入和输出之间存在同一种抽象类型关系时，可以使用泛型：

```py
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T:
    return items[0]
```
`T`可以理解为：先不知道具体是什么类型，但同一次使用过程中必须保持一致的“类型占位符”。

这样：

```py
first([1, 2, 3])      # 推断为int
first(["a", "b"])    # 推断为str
```
所以`T`最核心的意义是：表达不同位置之间的类型关系。

复杂泛型不需要刚开始就钻得很深，能够看懂SDK中常见的`T`、`Generic[T]`即可。

### 9. 类型标注不是运行时校验

例如：

```py
def add(a: int, b: int) -> int:
    return a + b
```

直接调用：

```py
add("a", "b")
```

Python运行时不会仅因为标注写了`int`就自动拒绝它。

FastAPI/Pydantic之所以能根据类型做运行时校验，是因为框架主动读取了这些类型信息并执行了额外逻辑。

## 十四、文件、路径与 JSON

### 1. 文件读写

最推荐使用`with`自动管理文件关闭：

```py
with open("data.txt", "r", encoding="utf-8") as file:
    content = file.read()
```

写文件：

```py
with open("result.txt", "w", encoding="utf-8") as file:
    file.write("hello\n")
```

常见模式：

- `"r"`：读取
- `"w"`：覆盖写入
- `"a"`：追加
- `"b"`：二进制模式，例如`"rb"`

逐行读取大型文本时，不一定需要一次性`read()`到内存，否则会把整个大文件内容一次性加载到内存：

```py
with open("data.txt", encoding="utf-8") as file:
    for line in file:
        print(line.rstrip("\n"))
```

文件对象本身可以迭代，这样一次读取一行，处理完再继续读取下一行，内存占用就会小很多。

### 2. `pathlib`

以前很多人写路径：

```py
base = "data"
path = base + "/" + "users.json"
```
这种字符串拼接容易产生平台和路径细节问题。

相比大量手工拼接路径字符串，现代Python中通常更推荐`pathlib.Path`：

```py
from pathlib import Path

base = Path("data")
file_path = base / "users.json"

print(file_path.name)#文件名：users.json
print(file_path.suffix)#扩展名：.json
print(file_path.exists())#文件是否存在
```
这里的`/`被`Path`重载了，表示路径拼接，即`data/users.json`。


创建目录：

```py
Path("output/logs").mkdir(parents=True, exist_ok=True)
```

这两个参数表示：如果父目录不存在就一起创建，目录已经存在也不要报错。

读取和写入小型文本文件：

```py
path = Path("hello.txt")
path.write_text("你好", encoding="utf-8")
content = path.read_text(encoding="utf-8")
```

### 3. JSON

JSON经常用于HTTP API、配置文件和数据交换。

Python对象 → JSON字符串，使用`dumps()`：

```py
import json

data = {"name": "Alice", "age": 20}
text = json.dumps(data, ensure_ascii=False)
```

JSON字符串 → Python对象，使用`loads()`：

```py
data = json.loads(text)
```

直接处理文件，使用`dump()`和`load()`：

```py
import json

with open("user.json", "w", encoding="utf-8") as file:
    json.dump({"name": "Alice"}, file, ensure_ascii=False, indent=2)

with open("user.json", "r", encoding="utf-8") as file:
    user = json.load(file)
```

这里的`ensure_ascii=False`是让中文不要写成`\u4f60\u597d`，而直接保存`你好`，而`indent=2`则是格式化缩进。

常见对应关系：

| JSON | Python |
|---|---|
| object | dict |
| array | list |
| string | str |
| number | int/float |
| true/false | True/False |
| null | None |

### 4. `os` 与环境变量

很多工程配置、API Key不会直接硬编码进代码，而是通过环境变量传入：

```py
import os

api_key = os.getenv("API_KEY")
```

操作系统环境中：`API_KEY=xxxxx`程序读取它，如果不存在，则返回None。

如果变量是必须的，也可以显式检查：

```py
api_key = os.environ["API_KEY"]
```

不存在时会抛出`KeyError`，因此能更早暴露配置缺失。

实际项目中常见`.env`文件，但`.env`不是Python标准库功能，一般由`python-dotenv`、Pydantic Settings等工具负责读取；敏感`.env`文件通常不应该提交到Git仓库。

## 十五、`with` 语句与上下文管理器

通常打开一个文件之后需要关闭：

```py
file = open("data.txt", "r", encoding="utf-8")
content = file.read()
file.close()
```

但如果读取过程中发生了异常，比如说:

```py
file = open("data.txt", "r", encoding="utf-8")

content = file.read()
result = 1 / 0

file.close()
```

则`file.close()`不会执行。

更安全的写法是使用try-finally语句：

```py
file = open("data.txt", "r", encoding="utf-8")

try:
    content = file.read()
finally:
    file.close()
```

而with语句把这种模式简化为：

```py
with open("data.txt", "r", encoding="utf-8") as file:
    content = file.read()
```

`with open(···) as f:`做了两件事：先由`open()`打开文件并返回文件对象，进入with代码块时把上下文管理器的进入结果赋值给f；离开代码块时自动关闭文件，不管代码块里是正常执行完毕还是抛出异常，文件都会被关闭。

with语句帮你省掉了异常语句和手动关闭文件，代码更简洁，也更不容易忘记释放资源。

### 1. 基本语法

```text
with 上下文管理器 [as 变量]:
    代码块
```
此处as变量可以省略，不加as的意思是：只执行上下文管理器的进入和退出逻辑，不需要接收`__enter__()`的返回值；使用`@contextmanager`时，这个值就是yield产生的值。


### 2. `with` 的工作原理

with语句并不是只能用于文件操作，任何实现了`__enter__`和`__exit__`魔术方法的对象都可以用with语句。

#### `__enter__()`

作用：进入with代码块之前，py会自动调用该魔术方法。

它通常负责：

- 打开或获取资源
- 执行初始化操作
- 返回as后面要使用的对象

##### a. 基本语法

```py
def __enter__(self):
    # 进入 with 前执行的操作
    return 返回值
```

参数：`self`

返回值：该方法的返回值会赋给`as`后面的变量。

```text
with 对象 as 变量：

#近似等价于：

变量 = 对象.__enter__()
```

#### `__exit__()`

作用：离开with代码块时，py会自动调用该方法。

通常负责：

- 关闭文件
- 断开数据库连接
- 释放锁
- 清理资源
- 处理异常

即使with内部发生异常，`__exit__()`通常也会执行。

##### a. 基本语法

```py
def __exit__(self, exc_type, exc_value, traceback):
    # 退出 with 时执行的操作
    return False  # 也可以根据需要返回True或None
```
参数：

- self：当前上下文管理器对象
- exc_type：异常类型
- exc_value：具体的异常对象，也就是错误信息。
- traceback：异常的调用栈信息，用于定位错误发生的位置

返回值：

- 若返回True：表示异常已经处理，不再继续抛出
- 若返回False或None：表示异常没有处理，继续向外抛出
- 注：不要随便返回True，否则错误会被静默吞掉，不容易发现问题，一般只在确定自己能够处理某种异常时才返回True


当你写`with obj as x`时，py会先调用`obj.__enter__()`，把返回值赋给x，然后执行with代码块，代码块结束后，不管是否会出错，都会调用`obj.__exit__()`做清理。

比如说下面这个例子，临时修改某个状态，用完自动恢复：

```py
class TempWorkDir:
    """临时切换工作目录，离开with块后自动恢复"""
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        import os
        self.old_dir = os.getcwd()  # 获取当前工作目录
        os.chdir(self.path)  # 切换到指定目录
        print(f"切换到：{os.getcwd()}")
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        import os
        os.chdir(self.old_dir)
        print(f"恢复到：{os.getcwd()}")
        return False

# 使用
import os
import tempfile
print(f"当前目录：{os.getcwd()}")

with TempWorkDir(tempfile.gettempdir()):
    print(f"with块内：{os.getcwd()}")

print(f"with块外：{os.getcwd()}")
```

### 3. `contextlib.contextmanager`
如果每次都要创建一个类来实现enter和exit两个魔术方法的话似乎有些麻烦，于是py的contextlib模块提供了一个装饰器，能够用更简洁的方式来写上下文管理器。

`yield`的作用是：

>返回一个值，并暂停函数；下次继续执行时，从暂停的位置往后运行

只要函数中出现了yield，这个函数就不再是普通函数，而是一个生成器函数。

yield的作用和return类似，只不过return的作用是返回结果并结束函数，而yield的作用是产生一个结果并暂停函数。调用包含yield的生成器函数时会得到一个生成器对象；生成器恢复执行后，可以从上次暂停的位置继续运行。

```py
from contextlib import contextmanager
import time

@contextmanager
def timer(label="代码块"):
    start = time.perf_counter()
    print(f"[{label}] 开始计时···")

    # yield之前的代码相当于__enter__
    # yield的值会赋给as后面的变量
    try:
        yield
    finally:
        # yield之后的代码相当于__exit__
        elapsed = time.perf_counter() - start
        print(f"[{label}] 耗时：{elapsed:.4f} 秒")

# 使用起来和类版本一样
with timer("求和"):
    total = sum(range(1000000))
    print(f"结果：{total}")
# 输出类似：
# [求和] 开始计时...
# 结果：499999500000
# [求和] 耗时：0.0xxx 秒
```

yield把函数分成两半：yield之前的代码在进入with块时执行，相当于`__enter__`，yield之后的代码在离开with块时执行，相当于`__exit__`，这样就不用每次都写一个带enter和exit的类了。

```py
@contextmanager
def manager():
    # __enter__ 部分
    resource = acquire_resource()

    try:
        yield resource
        # yield 出去的值绑定给 as 后面的变量
    finally:
        # __exit__ 部分
        release_resource(resource)
```
流程：

```text
执行 yield 之前的代码
        ↓
yield resource
        ↓
resource 绑定给 as 后面的变量
        ↓
执行 with 代码块
        ↓
恢复生成器
        ↓
执行 yield 之后的代码
```

再看一个例子，临时修改列表并自动恢复：

```py
from contextlib import contextmanager

@contextmanager
def temp_append(lst, item):
    """临时往列表末尾加一个元素，离开后自动移除"""
    lst.append(item)
    print(f"添加了{item}， 当前列表:{lst}")
    try:
        yield lst
    finally:
        lst.pop()
        print(f"移除了{item}，当前列表：{lst}")

data = [1,2,3]
print(f"原始列表:{data}")

with temp_append(data, 99) as d:
    print(f"with块内：{d}")

print(f"with块外：{data}")

```

**注：** 这个例子默认with代码块内部不会继续改变列表末尾，否则`pop()`移除的可能不是最开始添加的item。

整个过程大概是这样的：

1. 首先创建一个列表对象，而data指向这个列表，接着print。
2. 执行`with temp_append(data, 99) as d`，先计算`temp_append(data, 99)`，因此lst也指向data指向的列表对象，item赋值为99。
3. 因为函数被`@contextmanager`这个装饰器修饰，所以`temp_append(data, 99)`被包装成一个可以配合with使用的上下文管理器，进入with时，py开始执行`temp_append()`，一直运行到yield为止。
4. 接着开始执行yield之前的代码，给data指向的那个列表对象最后加上99。
5. 然后执行yield lst，第一步，函数暂停在这里，暂时不执行后面的finally，第二步，把lst交给as d，即让d指向lst，因此现在d, lst, data指向的都是同一个列表。
6. 接着开始执行with代码块内的代码，即`print(f"with块内：{d}")`，然后离开with代码块，从`yield lst`后面的代码开始执行，也就是finally部分的代码。
7. finally部分执行完之后，此时上下文管理器已经结束，最后执行with代码块后面的代码，即`print(f"with块外：{data}")`。


contextmanager 装饰的生成器必须正常地只 yield 一次；通常要用 try/finally 保证清理代码一定执行。若 with 中发生异常，异常会在生成器暂停的 yield 位置重新抛入。

---

**注：** py传参时，形参会绑定到实参所指向的同一个对象，不会自动复制对象；更准确地说，是对象引用按值传递，这适用于所有对象。

## 十六、算法题常用技巧

### 1. ACM 模式 I/O 模板

#### 输入处理

最基础的套路：`input()` 读一行，`split()` 按空格切分，`map(int, ...)` 批量转整数：

```py
# 读取一个整数
n = int(input())

for i in range(n):
    # 读取一行中的两个整数
    a, b = map(int, input().split())
    print(a + b)
# 输出：
# 3
# 7
# 11
```
如果一行有很多数字需要存到列表里：

```py
nums = list(map(int, input().split()))
```

#### `sys.stdin` 快速读取（大数据量）
当输入数据量很大（比如几十万行），input() 可能会超时。这时候需要用 sys.stdin 来加速读取。方法很简单，只需要在代码开头加一行：

```py
import sys
# 用 sys.stdin.readline 替换内置的 input
input = sys.stdin.readline

# 后面的代码跟之前完全一样
n = int(input())
for i in range(n):
    a, b = map(int, input().split())
    print(a + b)
```

**注：**`input = sys.stdin.readline`是算法竞赛中很常见的简写，但它会覆盖Python内置的`input()`名称，适合局部刷题代码；一般工程代码中不建议这样覆盖内置名称。

**注意：** `sys.stdin.readline` 读取的字符串末尾会带一个换行符 \n，但 split() 和 int() 会自动处理掉，所以大部分情况不需要额外操心。只有在直接拿字符串比较的时候要注意用 strip() 去掉末尾的换行。

#### 多组输入 / EOF
有些题目不告诉你有多少组输入，而是读到文件末尾（EOF）为止。这时候用 try-except 捕获异常。try 块中的代码如果发生`ValueError`，程序不会崩溃，而是跳到 except 块执行。这里利用这个机制检测输入结束：没有更多输入时，空字符串拆分后无法完成变量拆包，会被 except 捕获并执行 break 退出循环：

```py
import sys
input = sys.stdin.readline

while True:
    try:
        a, b = map(int, input().split())
        print(a + b)
    except ValueError:
        break
# 输出：
# 3
# 7
# 11
```

当 input() 读到 EOF 时，会返回空字符串，split() 得到空列表，map(int, ...) 拆包就会抛出`ValueError`，被 except 捕获后 break 跳出循环。注意，这种写法也会把格式错误导致的`ValueError`当成输入结束，因此下面直接遍历`sys.stdin`的写法通常更清晰。

还有一种更简洁的写法，直接用 sys.stdin 遍历每一行：

```py
import sys
for line in sys.stdin:
    a, b = map(int, line.split())
    print(a + b)
```

sys.stdin 本身就是一个可迭代对象，读完所有行自动结束，连 try-except 都不用写。对于按EOF读取多组输入，这通常是更清晰的首选写法。

### 2. 排序

#### `cmp_to_key`

##### a. 适用于必须两两比较才能定义顺序的场景
python中的排序通常使用key参数，大部分排序用 key 就够了，但有些场景需要两两比较才能定义顺序，比如经典的"最大数拼接"问题。这时候需要 cmp_to_key。

cmp_to_key函数就是把自定义的比较函数转化为key函数，便于排序。

一个标准的比较函数通常写成：

```py
def cmp(a, b):
    if a < b:
        return 负数
    elif a > b:
        return 正数
    else:
        return 0
```
返回值：

- 负数：a在前
- 0：两者相等
- 正数：a在后

##### b. 示例：最大数拼接

```py
from functools import cmp_to_key

# 例子：把数字拼接成最大的数
# 比如 [3, 30, 34] 应该拼成 "34330"
nums = [3, 30, 34, 5, 9]

# 自定义比较函数：比较 a+b 和 b+a 拼接后谁更大
# 返回负数表示 a 排前面，正数表示 b 排前面
def compare(a, b):
    if a + b > b + a:
        return -1  # a 排前面
    elif a + b < b + a:
        return 1   # b 排前面
    else:
        return 0

str_nums = [str(x) for x in nums]
str_nums.sort(key=cmp_to_key(compare))
result = "".join(str_nums)
print(f"最大拼接数：{result}")
# 输出：最大拼接数：953430
```

## 十七、并发与异步编程基础

### 1. 多线程：`threading`

py的threading模块提供了多线程编程的能力，最基本的用法是创建Thread对象，传入一个目标函数，然后调用start()启动线程。

其中：

```py
threading.Thread(
    target=target,
    args=args,
    kwargs=kwargs,
    name=name,
    daemon=daemon,
)
```
参数含义：

- target：线程要执行的函数；
- args：传给目标函数的位置参数；
- kwargs：传给目标函数的关键字参数；
- name：线程名称；
- daemon：是否为守护线程。

```py
thread.start()
```

表示真正启动一个新线程，在新线程中调用目标函数。

每个Thread对象只能调用一次start()

```py
thread.join()
```

join()的作用是让当前线程“等待”目标线程执行完毕。如果不调用join()，主线程会直接往下运行；但只要仍有非守护线程存活，整个Python进程通常不会立即退出。

```py

import threading
import time

def worker(name, seconds):
    print(f"线程 {name} 开始工作")
    # 用 sleep 模拟耗时操作
    time.sleep(seconds)
    print(f"线程 {name} 完成，耗时 {seconds} 秒")

# 创建两个线程对象
t1 = threading.Thread(target=worker, args=("A", 2))
t2 = threading.Thread(target=worker, args=("B", 1))

start = time.perf_counter()

# 启动线程
t1.start()
t2.start()

# 等待两个线程都执行完毕
t1.join()
t2.join()

end = time.perf_counter()
print(f"全部完成，总耗时 {end - start:.1f} 秒")

# 输出：
# 线程 A 开始工作
# 线程 B 开始工作
# 线程 B 完成，耗时 1 秒
# 线程 A 完成，耗时 2 秒
# 全部完成，总耗时 2.0 秒
```

再例如，用多线程模拟并发的网络请求：

```py
import threading
import time

def fetch_data(url, delay):
    print(f"开始请求{url}...")
    # 用sleep模拟网络请求耗时
    time.sleep(delay)
    print(f"请求{url}完成，耗时{delay}秒")

urls = [
    ("api/users", 2),
    ("api/orders", 3),
    ("api/products", 1),
]

# 同步方式：逐个请求
start = time.perf_counter()
for url, delay in urls:
    fetch_data(url, delay)
sync_time = time.perf_counter() - start
print(f"同步总耗时：{sync_time:.1f}秒\n")

# 多线程方式：并发请求
start = time.perf_counter()
threads = []
for url, delay in urls:
    t = threading.Thread(target=fetch_data, args=(url, delay))
    threads.append(t)
    t.start()

# 等待所有线程完成
for t in threads:
    t.join()
thread_time = time.perf_counter() - start
print(f"多线程总耗时：{thread_time:.1f} 秒")
```

输出：

```text
开始请求api/users...
请求api/users完成，耗时2秒
开始请求api/orders...
请求api/orders完成，耗时3秒
开始请求api/products...
请求api/products完成，耗时1秒
同步总耗时：6.0秒

开始请求api/users...
开始请求api/orders...
开始请求api/products...
请求api/products完成，耗时1秒
请求api/users完成，耗时2秒
请求api/orders完成，耗时3秒
多线程总耗时：3.0 秒
```
### 2. 线程安全、竞态条件与锁

多线程确实很方便，但当多个线程同时修改同一份数据时，可能会出错，这也叫做**竞态条件：**

>程序结果取决于多个执行单元不可预测的执行顺序。

不能因为某次运行恰好得到正确结果，就认为代码是安全的。

例如，两个线程各自给一个全局变量加1一万次，最终结果理论上应该是两万，但实际按下面这样操作的话，结果不一定会是两万。

```py
import threading

counter = 0

def increment(n):
    # global 声明：在函数内部修改函数外部定义的变量时需要加这行
    # 不加的话，Python 会把 counter 当作函数内的局部变量
    global counter
    for _ in range(n):
        counter += 1

# 两个线程各加 10000 次
t1 = threading.Thread(target=increment, args=(10000,))
t2 = threading.Thread(target=increment, args=(10000,))
# 注：当元组中只有一个参数时，仍然要加逗号

t1.start()
t2.start()
t1.join()
t2.join()

# 期望 20000，但代码逻辑上存在竞态条件
print(f"期望值：20000")
print(f"实际值：{counter}")
print(f"结果正确？{counter == 20000}")
```
你可能发现某次运行结果恰好是正确的20000，但这不能说明代码安全。CPython的GIL（全局解释器锁，后面会详细讲）不保证`counter += 1`这样的复合操作具有原子性；换一个Python版本、实现或稍微改变操作方式，竞态就可能暴露出来。

因为`counter += 1`看起来是一步，实际上分为三步：

```text
读取 counter
计算 counter + 1
把新值写回 counter
```

当两个线程共同执行的时候，可能会发生这样的情况：

```text
线程 A 读取 counter = 10
线程 B 读取 counter = 10

线程 A 计算出 11
线程 B 计算出 11

线程 A 写入 11
线程 B 写入 11
```

所以只要涉及多个线程共同访问共享可变数据，就需要使用合适的同步方式，例如锁或Queue。锁保证同一时刻只有一个线程能执行被保护的代码。

```py
import threading

counter = 0
lock = threading.Lock()

def increment(n):
    global counter
    for _ in range(n):
        # 推荐使用with自动管理锁的获取和释放
        with lock:
            counter += 1

t1 = threading.Thread(target=increment, args=(10000,))
t2 = threading.Thread(target=increment, args=(10000,))

t1.start()
t2.start()
t1.join()
t2.join()

print(f"期望值：20000")
print(f"实际值：{counter}")
print(f"结果正确？{counter == 20000}")
```

`with lock:`会在进入代码块时自动获取锁，离开时自动释放，是实际编程中更推荐的写法。

如果手动管理锁，更准确的写法应使用`try/finally`保证发生异常时也能释放锁：

```py
lock.acquire()
try:
    counter += 1
finally:
    lock.release()
```

#### 临界区与锁粒度

被锁保护的代码称为临界区。

锁的范围不应该无脑扩大，这样其他线程会长时间等待，基本失去并发意义。

不过，加锁虽然保证了安全，但也降低了性能，线程需要排队等锁，就不能真正并发执行被锁保护的那段代码了，所以锁只应该保护**必须互斥访问的最小代码段。**

通常应该只保护共享数据操作：

```py
result = calculate_something()

with lock:
    shared_results.append(result)
```

#### 死锁

假设线程A：

```py
with lock_a:
    with lock_b:
        ...
```

线程B：

```py
with lock_b:
    with lock_a:
        ...
```

这样可能就会出现：

```text
线程 A 拿到了 lock_a，等待 lock_b
线程 B 拿到了 lock_b，等待 lock_a
```

双方互相等待，永远无法继续，这就是死锁。

#### 线程间数据传递：优先考虑 `Queue`

比起多个线程共同修改一个列表，更安全的方式常常是使用：

```py
from queue import Queue

# 生产者
def producer(queue):
    for number in range(5):
        queue.put(number)
    
    queue.put(None)
# 消费者
def consumer(queue):
    while True:
        item = queue.get()
        try:
            if item is None:
                break
            print("处理：", item)
        finally:
            queue.task_done()
```

queue.Queue内部已经实现了必要的同步机制，专门用于在线程之间安全传递任务或数据。

有一句并发编程中的老话很实用：

>能传递消息，就尽量不要共享可变状态。

#### 更高层的线程池：`ThreadPoolExecutor`

前面的`threading.Thread`适合用来理解线程的创建、启动和等待。如果实际需求只是“把一批独立任务交给线程并发执行”，标准库`concurrent.futures`提供了更高层的线程池接口：

```py
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(fetch_data, url, delay)
        for url, delay in urls
    ]

    # 等待所有任务完成，并在这里重新抛出任务中的异常
    for future in futures:
        future.result()
```

`ThreadPoolExecutor`会复用线程，不需要自己逐个创建和管理`Thread`对象。学习线程原理时仍然应该先理解`Thread`、`start()`和`join()`，实际批量执行I/O任务时则可以优先考虑线程池。


### 3. 全局解释器锁（GIL）及其影响

在默认启用GIL的CPython构建中，GIL即全局解释器锁，它通常限制同一进程内同时只有一个线程执行py字节码。Python从3.13开始还提供可选的free-threaded构建，可以禁用GIL，但它并不是传统默认构建。

在默认启用GIL的CPython中，对于纯py的CPU密集型任务（大量计算），多线程通常不会更快，甚至可能更慢。

因为即使你开了多个线程，同一时刻也只有一个线程在执行py代码，其他线程在等着。

```py
import threading
import time

def cpu_work(n):
    """CPU密集任务：计算累加"""
    total = 0
    for i in range(n):
        total += i
    return total

N = 5_000_000

# 单线程：串行执行两次
start = time.perf_counter()
cpu_work(N)
cpu_work(N)
single_time = time.perf_counter() - start
print(f"单线程耗时：{single_time:.2f} 秒")

# 多线程：两个线程各执行一次
start = time.perf_counter()
t1 = threading.Thread(target=cpu_work, args=(N,))
t2 = threading.Thread(target=cpu_work, args=(N,))
t1.start()
t2.start()
t1.join()
t2.join()
multi_time = time.perf_counter() - start
print(f"多线程耗时：{multi_time:.2f} 秒")

print(f"多线程 vs 单线程：{multi_time / single_time:.2f}x")
```

输出：

```text
单线程耗时：0.26 秒
多线程耗时：0.25 秒
多线程 vs 单线程：0.96x
```

但是对于I/O密集型任务，如网络请求、文件读写、数据库查询等，多线程依然有效，因为GIL在线程执行I/O操作时会释放，让其他线程有机会执行。

如果你确实需要并行计算CPU密集型任务，可以用multiprocessing模块，它会启动真正的子进程，每个进程有自己的独立的py解释器和GIL，可以充分利用多核CPU。

```py
from multiprocessing import Process

if __name__ == "__main__":
    # 用法和 threading.Thread 几乎一样
    p1 = Process(target=cpu_work, args=(N,))
    p2 = Process(target=cpu_work, args=(N,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
```

在Windows等使用spawn方式创建子进程的环境中，应当使用`if __name__ == "__main__":`保护创建进程的代码，避免子进程重新导入主模块时再次创建进程。

#### 更高层的进程池：`ProcessPoolExecutor`

如果实际需求是把一批彼此独立的CPU任务分发到多个进程，`concurrent.futures`也提供了更高层的进程池接口：

```py
from concurrent.futures import ProcessPoolExecutor

if __name__ == "__main__":
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(cpu_work, [N, N]))
```

它和`ThreadPoolExecutor`使用方式相近，但底层使用多个进程，适合默认启用GIL的CPython中的纯Python CPU密集型任务。

### 4. 异步编程：`asyncio`

除了多线程，py还有另一种并发方式：异步编程。典型的asyncio事件循环可以在一个线程内实现并发，靠的是“协程”这个概念。

协程不是线程，而是“可暂停的任务”。一个任务等待时，暂时把执行权交给其他任务。

也叫**协作式并发。**


>协程是一段可以执行到一半暂停，之后再从原位置继续执行的代码。

py用`async def`定义**协程函数**，用`await`等待一个可等待对象。`await`是潜在的暂停点：如果等待结果还没完成，当前协程可以暂停并让事件循环执行其他任务；如果结果已经完成，也可能直接继续运行。

**协程对象**：调用协程函数得到的对象。

此时一般还没有正式开始运行。

**任务Task**：将协程提交给事件循环调度后，可以包装成任务：

```py
task = asyncio.create_task(download())
```

`Task`可以理解为：已经登记到事件循环中，准备并发执行的协程。

```py
import asyncio
import time

# 用async def定义协程函数
async def say_hello(name, delay):
    print(f"{name} 开始")
    # 下面这行模拟异步等待
    # 等待期间，事件循环可以去执行其他协程
    await asyncio.sleep(delay)
    print(f"{name} 完成，等了 {delay} 秒")

async def main():
    start = time.perf_counter()

    # 按顺序执行：先等A完成，再等B完成，总耗时仍为3秒
    await say_hello("A", 2)
    await say_hello("B", 1)

    end = time.perf_counter()
    print(f"顺序执行总耗时：{end - start:.1f} 秒")

asyncio.run(main())
```

`asyncio.run()`是启动异步程序的入口，它会创建一个事件循环并运行传入的协程，等待协程执行完成之后，关闭事件循环。

上面的例子中，await say_hello("A", 2) 会等 A 完成再执行 B，所以总耗时还是 3 秒，跟同步没什么区别。

#### `asyncio.create_task()` 与 `Task`

```py
async def main():
    task_a = asyncio.create_task(work("A", 2))
    task_b = asyncio.create_task(work("B", 1))

    print("任务已经创建")

    await task_a
    await task_b
```

区别是：

```py
coro = work("A", 2)
```

只是创建协程对象，不会自动调度。

而：

```py
task = asyncio.create_task(coro)
```

会把协程包装成`Task`并安排它尽快运行。

官方文档把`Task`定义为被调度并发运行的协程，并建议保存`create_task()`返回的引用。


#### 事件循环

事件循环的过程大致如下：

```text
检查哪些协程现在可以执行
        ↓
选择一个协程运行
        ↓
协程遇到 await，暂停
        ↓
切换到另一个可执行协程
        ↓
某个协程等待的结果完成
        ↓
把对应协程重新放回可执行队列
```
在一个典型的单线程事件循环中，同一瞬间只有一个任务在执行py代码，任务执行到能够挂起的await时，事件循环才有机会调度其他任务。

#### 使用 `asyncio.gather()` 并发运行

要并发执行多个协程，可以使用`asyncio.gather()`：

```py
import asyncio
import time

async def fetch_data(url, delay):
    print(f"开始请求 {url} ...")
    await asyncio.sleep(delay)
    print(f"请求 {url} 完成，耗时 {delay} 秒")   
    return f"{url} 的数据"

async def main():
    start = time.perf_counter()

    # 用gather并发执行多个协程
    results = await asyncio.gather(
        fetch_data("api/users", 2),
        fetch_data("api/orders", 3),
        fetch_data("api/products", 1),
    )

    end = time.perf_counter()
    print(f"\n并发总耗时：{end - start:.1f} 秒")
    print(f"返回结果：{results}")

asyncio.run(main())
```

`asyncio.gather()`接收多个协程，并把它们并发调度运行。返回结果时，会按照传入参数的顺序排列。

当一个协程遇到await进入等待时，事件循环会自动切换到其它协程继续执行。对于彼此独立、等待时间可以重叠的任务，总耗时通常接近最慢的那个，而不是所有耗时相加。

asyncio 和多线程有什么区别？在典型的单线程事件循环中，协程在await处协作式地让出执行权；多线程则由操作系统在线程之间进行调度。

但你的代码必须是"异步风格"的，普通函数不能直接变成协程，阻塞操作（比如 time.sleep()）也不能直接用在协程里（要用 asyncio.sleep()）。

#### 结构化并发：`TaskGroup`

从py 3.11开始，还可以使用结构化并发：

```py
import asyncio

async def main():
    async with asyncio.TaskGroup() as group:
        task_a = group.create_task(work("A", 2))
        task_b = group.create_task(work("B", 1))
    
    print("所有任务都已经结束")
```

而退出`async with asyncio.TaskGroup()`时，会自动等待组内任务。如果其中一个任务异常失败，`TaskGroup`会取消其他相关任务，并在退出时统一处理异常。相比散落的`create_task()`，它更容易保证任务不会被遗忘。对于一组生命周期彼此相关的任务，现代`asyncio`代码通常优先考虑这种结构化并发写法。

### 5. 并发方案如何选择

- **I/O 密集型任务**（网络请求、文件读写、数据库查询）：asyncio 和 threading 都行。asyncio 在高并发场景下性能更好（单线程没有线程切换开销），但需要用异步风格编写代码。threading 更直观，现有的同步代码改造成本低。

- **CPU 密集型任务**（大量数值计算、图像处理、加密解密）：在默认启用GIL的CPython中，通常使用multiprocessing实现多核并行。threading对纯py CPU密集任务通常没有加速效果；释放GIL的扩展代码或free-threaded构建属于例外。

- **简单场景**：用 threading 最省心，API 简单直观，几行代码就能用起来。

- **高并发 I/O 场景**：用 asyncio。比如同时发起上百个网络请求，asyncio 的性能比开上百个线程好得多。

### 6. `asyncio` 常见注意事项

#### 异步代码中的阻塞函数

错误示例：

```py
import time


async def work():
    time.sleep(5)
    # 上面这一行会直接阻塞事件循环线程，在这5秒内，其他协程也无法运行，整个事件循环停住
```

应该使用：

```py
async def work():
    await asyncio.sleep(5)
    # 当前协程挂起，事件循环运行其他任务
```

同理，在异步函数里直接调用阻塞式网络库、数据库驱动或耗时 CPU 函数，也可能把整个事件循环卡住。官方文档明确警告不要直接在事件循环线程中运行阻塞或 CPU 密集代码。

假如一定要调用同步阻塞函数，那么可以使用：

```py
await asyncio.to_thread(sync_function, arg1, arg2)
```

例如：

```py
import asyncio
import time


def blocking_work():
    time.sleep(2)
    return "完成"


async def main():
    result = await asyncio.to_thread(blocking_work)
    print(result)


asyncio.run(main())
```

这会把同步阻塞函数放到另一个线程中执行，避免堵住事件循环。

适合：

- 暂时无法替换的同步库
- 阻塞式文件操作
- 阻塞式网络API
- 已有同步项目异步迁移
  
对于纯Python CPU密集计算，在默认CPython下更适合使用进程池，而不是简单地`to_thread`。

#### 异步代码中的竞态条件

`asyncio`是单线程，但这并不意味着它没有竞态条件，单线程意味着两个协程不会在任意机器指令中间被操作系统强制同时运行，但只要代码在共享状态操作过程中出现`await`，其他协程就可以插进来。

例如：

```py
import asyncio

counter = 0

async def increase():
    global counter

    old_value = counter
    await asyncio.sleep(0)
    counter = old_value + 1
```

运行两个任务：

```py
async def main():
    await asyncio.gather(
        increase(),
        increase(),
    )

    print(counter)

asyncio.run(main())
```

可能过程是：

```text
任务 A 读取 counter = 0
任务 A 遇到 await

任务 B 读取 counter = 0
任务 B 遇到 await

任务 A 写入 1
任务 B 写入 1
```

因此异步代码也有`asyncio.Lock()`

```py
lock = asyncio.Lock()

async def increase():
    global counter

    async with lock:
        counter += 1
```

Python 标准库专门提供了 `asyncio.Lock、Event、Semaphore` 等同步原语，这本身就说明异步任务也存在共享状态协调需求；这些原语用于协程之间，不用于操作系统线程之间。

#### `async with` 与异步上下文管理器

普通上下文管理器实现：

```py
__enter__()
__exit__()
```

异步上下文管理器实现：

```py
__aenter__()
__aexit__()
```

使用：

```py
async with resource:
    ...
```
适用于进入或退出上下文时本身需要等待的资源，例如：

- 异步数据库连接
- 异步HTTP会话
- 异步锁
- `TaskGroup`
- 异步文件或网络资源

也可以使用：

```py
from contextlib import asynccontextmanager
```

例如：

```py
from contextlib import asynccontextmanager

@asynccontextmanager
async def database_connection():
    connection = await open_connection()

    try:
        yield connection
    finally:
        await connection.close()
```

使用：

```py
async with database_connection() as connection:
    await connection.query(...)
```

官方contextlib提供了asynccontextmanager，用于通过异步生成器实现async with。

再看一个例子：

```py
import asyncio
from functools import wraps
from time import perf_counter


def async_timer(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = perf_counter()

        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = perf_counter() - start
            print(f"{func.__name__} 耗时：{elapsed:.3f} 秒")

    return wrapper


@async_timer
async def async_work():
    await asyncio.sleep(2)


asyncio.run(async_work())
```
这段代码实现的是一个异步计时装饰器，给异步函数加上计时功能，并且不改变原异步函数的调用方式。

`@wraps(func)`是带参数的装饰器，代码：

```py
@wraps(func)
async def wrapper(*args, **kwargs):
    ...
```

等价于：

```py
async def wrapper(*args, **kwargs):
    ...

wrapper = wraps(func)(wrapper)
```

这里看起来有两次调用，可以拆成：

```py
decorator = wraps(func)
wrapper = decorator(wrapper)
```

也就是：

1. `wraps(func)`根据原函数func创建一个装饰器
2. 再用这个装饰器处理wrapper
3. 把处理后的函数重新赋值给wrapper

为什么是`@wraps(func)`，不是`@wraps`？因为wraps需要先知道要保留哪一个原函数的信息，就可以把func的名称，文档等信息复制给下面的wrapper。

#### 异步函数的装饰器

假设：

```py
@timer
async def async_work():
    await asyncio.sleep(2)
```

如果timer的包装函数是普通函数：

```py
def wrapper(*args, **kwargs):
    return func(*args, **kwargs)
```

那么它得到的只是协程对象，并没有等待协程真正执行。因此计时结果可能接近0

异步计时装饰器的实现如下：

```py
import asyncio
from functools import wraps
from time import perf_counter

def async_timer(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = perf_counter()
        
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = perf_counter() - start
            print(f"{func.__name__}耗时：{elapsed:.3f}秒")
    
    return wrapper

@async_timer
async def async_work():
    await asyncio.sleep(2)

asyncio.run(async_work())
```

其中`perf_counter()`用来精确测量时间间隔：

```py
start = perf_counter()
# 执行某段代码
elapsed = perf_counter() - start
```

这里得到的`elapsed`就是这段代码经过的实际时间，`perf_counter()`比`time.time()`更适合性能计时。

上述过程大致为：

- 程序加载阶段：
    ```text
    1. 导入 wraps 和 perf_counter

    2. 定义 async_timer
    只创建函数，不执行函数体

    3. 定义原来的 async_work

    4. 发现 @async_timer

    5. 执行：
    async_work = async_timer(原来的 async_work)

    6. async_timer 返回 wrapper

    7. 现在：
    async_work → wrapper
    wrapper 通过闭包记住原函数 func
    ```
- 程序运行阶段：
    ```text
    执行：asyncio.run(async_work())

    过程是：
    1. async_work()
    实际调用 wrapper()
    创建 wrapper 协程对象

    2. asyncio.run() 创建事件循环

    3. 事件循环开始运行 wrapper

    4. wrapper 记录开始时间

    5. 执行 await func()
    调用原来的 async_work

    6. 原函数执行 await asyncio.sleep(2)

    7. 原函数暂停两秒

    8. 两秒后恢复原函数

    9. 原函数执行结束，返回 None

    10. wrapper 准备返回 None

    11. 先执行 finally

    12. 计算并打印耗时

    13. wrapper 返回 None

    14. asyncio.run() 结束并关闭事件循环

    最终输出类似为：
    async_work 耗时：2.002 秒
    ```

为什么必须使用`await`：因为调用异步函数只会创建协程对象，不会等待它执行完成，因此，如果直接写成`return func(*args, **kwargs)`的话，会直接返回协程对象，计时器也无法覆盖原函数真正执行的过程。

写成`return await func(*args, **kwargs)`，就是运行异步函数，并等待它执行完成，再取得它的返回值。

### 7. 异步迭代器与异步生成器

普通`for`循环对应同步迭代协议，而某些数据本身需要“等待之后才能产生下一个值”，例如：

- 流式LLM响应
- WebSocket消息
- 异步数据库游标
- 分页网络数据流

这个时候会使用`async for`。

#### 异步生成器

只要在`async def`中使用`yield`，就会得到异步生成器函数：

```py
import asyncio

async def count():
    for i in range(3):
        await asyncio.sleep(0.5)
        yield i


async def main():
    async for value in count():
        print(value)


asyncio.run(main())
```

它可以理解为：

>普通生成器负责“按需产生值”，异步生成器则允许在产生下一个值之前先执行异步等待。

#### 异步迭代协议

异步可迭代对象通常实现：

```py
__aiter__()
__anext__()
```

`async for`会不断等待：

```py
await iterator.__anext__()
```

直到抛出`StopAsyncIteration`。

正常开发中一般不需要频繁手写`__aiter__`和`__anext__`，异步生成器通常更加简洁。

### 8. `asyncio.timeout()`（Python 3.11+）

网络请求、Agent工具等操作不能无限等待，可以给一段异步代码设置超时：

```py
import asyncio

async def slow_work():
    await asyncio.sleep(10)


async def main():
    try:
        async with asyncio.timeout(2):
            await slow_work()
    except TimeoutError:
        print("操作超时")


asyncio.run(main())
```

在Agent和后端工程中，“超时”本身就是正常的失败模式之一，不应该默认让一个外部调用永远阻塞整个任务。
