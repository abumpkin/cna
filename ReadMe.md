# cna

一个根据配置文件发送一系列 http 请求的工具.

## 快速入门

<TODO do="场景, 分析, 配置"/>

```json
{
  "connect_timeout": 1000,
  "retry_interval": 500,
  "default_target": "precheck",
  "process_ifs": ["WLAN"],
  "variables_map": {
    "MAC": "if_mac",
    "IP": "if_ip",
    "REDIRECTED": "target_redirected"
  },
  "variables": {
    "USERNAME": "xxx",
    "PASSWD": "xxx"
  },
  "targets": {
    "precheck": {
      "url": "http://www.baidu.com",
      "method": "GET",
      "retry": 1,
      "check": "REDIRECTED == True",
      "next": "auth"
    },
    "auth": {
      "url": "http://xxx/login",
      "method": "POST",
      "payload": {
        "usrname": "{USERNAME}",
        "passwd": "{PASSWD}",
        ...
      },
      "retry": 5,
      "check": "True",
      "next": "check"
    },
    "check": {
      "url": "http://www.baidu.com",
      "method": "GET",
      "retry_interval": 2000,
      "retry": 2,
      "check": "REDIRECTED != True"
    },
    ...
  }
}
```

## 内置变量

* `all_ifs`: 字典. 配置文件中 `process_ifs` 定义的所有接口的信息.

  键为 `process_ifs` 列表里的接口名, 值为一个五元组 (索引, 名称, 友好名称, IP 地址, 物理地址).
* `cur_if`: 字符串, 当前正在处理的接口, 值为配置文件中 `process_ifs` 列表里的值.
* `if_mac`: 字符串, 当前正在处理接口的 MAC 地址. (以 `-` 作为分隔符)
* `if_ip`: 字符串, 当前正在处理接口的 IP 地址.
* `target_status_code`: 集合, 当前 Target 请求的响应的状态码集合, 收集重定向过程直到结束产生的所有状态码.
* `target_redirected`: bool 类型, 当前 Target 请求发生重定向.
* `url_response`: IO 类型, url 响应文件对象.
* `current_target`: 字符串, 当前执行的目标.
* `next_target`: 字符串, 下一个要执行的目标

通过 `loadpy()` 执行的文件能够访问所有的内置变量和配置文件里定义的变量.

## 配置文件

```json
{
  [通用配置],
  "default_target": "precheck",
  "process_ifs": ["WLAN"],
  "variables": {
    "变量名": "值",
    ...
  },
  "variables_map": {
    "变量名": "内置变量名",
    ...
  },
  "targets": {
    [目标配置, ...]
  }
}
```

* `default_target`: 定义程序运行后默认执行的第一个 **目标**.
* `process_ifs`: 列表, 定义分别需要对哪些网络接口(网卡)执行 **目标**.
* `variables`: 对象, 定义的变量可用于 **目标配置** 中的 `pyload` 对象中或者 `check` 中.
* `variables_map`: 将一个自定义变量映射到一个 **内置变量** 中, 可用的内置变量见 [内置变量](#内置变量).
* `targets`: 对象, 里面的键和值对应 **目标** 名称和目标定义.

**通用配置**:

可出现在 **根** 对象和 **目标** 对象中.

* `connect_timeout`: int 类型, 连接超时时间, 单位毫秒.
  * 出现在 **根** 对象中: 设置默认连接超时时间.
  * 出现在 **目标** 对象中: 设置特定目标的连接超时时间.
* `retry_interval`: int 类型, 检查失败后重试的间隔时间, 单位毫秒.
  * 出现在 **根** 对象中: 设置默认重试的间隔时间.
  * 出现在 **目标** 对象中: 设置特定目标的重试的间隔时间.
* `retry`: int 类型, 失败后的重试次数.
  * 出现在 **根** 对象中: 设置默认重试次数.
  * 出现在 **目标** 对象中: 设置特定目标的重试次数.

**目标配置**:

```json
"目标名": {
  [通用配置],
  "url": "xxx",
  "method": "POST | GET | None",
  "payload": { ... },
  "check": "expr",
  "next": "next-target"
}
```

* 通用配置: 可以选择使用 **通用配置** 里的配置项.
* `url`: 要发起请求的 URL.
* `method`: 发起 HTTP 请求使用的方法, 如果为 None 或不配置此项或为其他值则不发起请求, 此 **目标** 将直接进行 `check` 判断.
* `payload`: 值为一个对象, 里面的键值对作为数据发送.
  * 行为:
    * **GET** 方法: 将数据作为 URL 参数.
    * **POST** 方法: 将数据作为 HTTP 报文数据部分以 *application/x-www-form-urlencoded* 形式传送.
  * 键值: 在值中可以使用变量, 如 `"payload": {"foo": "{bar}"}`, 并在 **根** 配置中的 `variables` 或 `variables_map` 中定义了 `bar` 则自动把 "{bar}" 替换成变量对应的值.
* `check`: 用来判断此 **目标** 是否成功, 其值为一个 python 语法的表达式. 表达式计算的结果为 `True` 则表示 **目标** 执行成功, `False` 表示失败. 表达式里提供以下特殊的函数:
  * `loadpy(filename)`: 加载同配置文件目录下的 python 文件并执行. 比如使用 `loadpy('a.py').func()`, 将加载 "a.py" 文件并调用其中的 "func()" 函数, `func` 函数因返回能够进行 bool 判断的值, 以表示 **目标** 执行结果成功与否.
* `next`: 其值为一个已定义的 **目标** 的名称. 表示如果此 **目标** 执行成功, 将要执行的下一个 **目标**.

## 命令行参数

* `-c`: 指定配置文件
* `-I`: 指定接口列表, 逗号分隔
* `-i`: 列出所有可用接口
* `-l`: 列出所有目标
* `-t`: 指定执行目标

## 平台

## 声明








