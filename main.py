import pprint
import os, sys, time, socket
from ConfigManager import ConfigManager
from LogHandler import LogHandler
from LogHandler import LOG_LEVELS
import urllib.request
from urllib.request import Request
import http
import http.cookiejar
from http.cookiejar import Cookie
import urllib.parse
import InterfacesInfo

# 默认超时时间
DEFAULT_TIMEOUT = 1000

# 格式打印
pout = pprint.PrettyPrinter(indent=2, depth=5).pprint

# 日志处理对象
LogHelper = LogHandler()
# 日志输出分类
LOG_CATEGORIES = LogHelper.LOG_CATEGORIES

# 配置里的变量
UserVariables = {}
# 内置变量
BuiltinVariables = {
    # 所有接口
    "all_ifs": {},
    # 当前接口
    "cur_if": "",
    # 当前接口的 MAC 地址
    "if_mac": "",
    # 当前接口的 IP 地址
    "if_ip": "",
    # 当前 Target 请求的响应的状态码集合, 收集重定向过程直到结束产生的所有状态码.
    "target_status_code": set(),
    # 当前 Target 请求发生重定向
    "target_redirected": False,
    # url 响应文件对象
    "url_response": None,
    # 是否超时且请求失败
    "timed_out": False,
    # 当前执行的目标
    "current_target": "",
    # 下一个要执行的目标
    "next_target": ""
}


# 重定向检查; 状态码检测
class RedirectChecker(urllib.request.HTTPRedirectHandler):
    def init(self, req):
        BuiltinVariables["target_redirected"] = False
        BuiltinVariables["target_status_code"].clear()

    def http_request(self, req):
        try:
            if not req.redirect_dict:
                raise Exception()
        except:
            self.init(req)
        return req

    def https_request(self, req):
        return self.http_request(req)

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        LOG_CATEGORIES.REQUEST_REDIRECT(LOG_LEVELS.INFO, code, msg)
        res = super().redirect_request(req, fp, code, msg, hdrs, newurl)
        BuiltinVariables["target_redirected"] = True
        return res

    def http_response(self, req, res):
        BuiltinVariables["target_status_code"].add(res.status)
        return res

    def https_response(self, req, res):
        return self.http_response(req, res)

# 数据发送接口设置
class MHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, src):
        super().__init__()
        self.srcAddr = (src, 0)

    def http_open(self, req):
        return self.do_open(http.client.HTTPConnection, req,
                            source_address=self.srcAddr)

class MHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, src, **kwargs):
        super().__init__(**kwargs)
        self.srcAddr = (src, 0)

    def http_open(self, req):
        return self.do_open(http.client.HTTPSConnection, req,
            context=self._context, check_hostname=self._check_hostname,
            source_address=self.srcAddr)

# url 请求器
cookieJar = http.cookiejar.CookieJar()
def UpdateRequester(srcAddr=None):
    global Requester
    cookieHandler = urllib.request.HTTPCookieProcessor(cookieJar)
    Requester = urllib.request.build_opener(
        MHTTPHandler(srcAddr), MHTTPSHandler(srcAddr), RedirectChecker(), cookieHandler)

UpdateRequester()

def QueryAllVariables() -> dict:
    ret = UserVariables.copy()
    # 内置变量映射到配置文件中的映射变量
    try:
        vars_map = CONF.variables_map
        for varname, biVarname in vars_map.items():
            if biVarname not in BuiltinVariables:
                LOG_CATEGORIES.VARIABLE_BUILTIN_NOT_FOUND(
                    LOG_LEVELS.ERROR, varname, biVarname)
                exit(-1)
            ret[varname] = BuiltinVariables[biVarname]
    except Exception as e:
        LOG_CATEGORIES.CONFIG_PROP_NOT_FOUND(LOG_LEVELS.INFO, e.args[1])
    return ret


class Target:
    def __init__(self, target_name, target_info):
        self.target_info = target_info
        self.name = target_name
        self.payload = {}
        self.next = ""
        self.url = ""
        try:
            self.retry = int(CONF.retry)
        except:
            self.retry = 1
        self.check = "True"

        try:
            self.method = target_info["method"]
            if self.method == "None" or self.method == None:
                self.method = ""
            elif self.method not in ["GET", "POST"]:
                LOG_CATEGORIES.HTTP_METHOD_UNKNOWN(
                    LOG_LEVELS.CAVEAT, self.name, self.method)
                raise Exception()
        except Exception as e:
            LOG_CATEGORIES.TARGET_NO_METHOD_MATCHED(
                LOG_LEVELS.INFO, self.name)
            self.method = None
        if self.method:
            try:
                self.url = target_info["url"]
            except Exception as e:
                LOG_CATEGORIES.CONFIG_TARGET_PROP_NOT_FOUND(
                    LOG_LEVELS.ERROR, self.name, "url")
                exit(-1)
            try:
                self.payload = target_info["payload"]
            except Exception as e:
                LOG_CATEGORIES.CONFIG_TARGET_PROP_NOT_FOUND(
                    LOG_LEVELS.INFO, self.name, "payload")
        try:
            self.retry = int(target_info["retry"])
        except Exception as e:
            LOG_CATEGORIES.CONFIG_TARGET_PROP_NOT_FOUND(
                LOG_LEVELS.INFO, self.name, "retry")
        try:
            self.next = target_info["next"]
        except Exception as e:
            pass
        try:
            self.check = target_info["check"]
        except Exception as e:
            LOG_CATEGORIES.CONFIG_TARGET_PROP_NOT_FOUND(
                LOG_LEVELS.ERROR, self.name, "check")
            exit(-1)

    def Request(self) -> bool:
        if self.method == None:
            return True
        data = {}
        # 将变量替换成值
        def data_var_mapping():
            realVars = QueryAllVariables()
            for k, v in data.items():
                data[k] = v.format_map(realVars)
        try:
            url_secs = urllib.parse.urlsplit(
                self.url, scheme="http", allow_fragments=False)
            if self.method == "GET":
                data.update(urllib.parse.parse_qs(url_secs.query))
                data.update(self.payload)
                data_var_mapping()
                url_secs = [*url_secs]
                url_secs[3] = urllib.parse.urlencode(data)
                reqUrl = urllib.parse.urlunsplit(url_secs)
                reqInfo = Request(reqUrl)
            else:
                data.update(self.payload)
                data_var_mapping()
                reqData = urllib.parse.urlencode(data)
                reqInfo = Request(self.url, data=reqData.encode("utf8"))
        except:
            LOG_CATEGORIES.URL_NOT_VALID(LOG_LEVELS.ERROR, self.name, url)
            raise Exception()
        # 加载超时配置
        try:
            if "connect_timeout" in self.target_info:
                timeout = int(self.target_info["connect_timeout"]) / 1000
            else:
                timeout = int(CONF.connect_timeout) / 1000
        except Exception as e:
            timeout = DEFAULT_TIMEOUT
            LOG_CATEGORIES.CONFIG_PROP_NOT_FOUND(LOG_LEVELS.INFO, e.args[1])
            LOG_CATEGORIES.TIMEOUT_NOT_SET(LOG_LEVELS.INFO, ConnectTimeout)
        try:
            dataResponse = Requester.open(reqInfo, timeout=timeout)
            LOG_CATEGORIES.TARGET_RESPONSE_CODE(
                LOG_LEVELS.INFO, self.name, dataResponse.status)
            BuiltinVariables["url_response"] = dataResponse
        except urllib.request.URLError as err:
            LOG_CATEGORIES.PYTHON_EXCEPTION(LOG_LEVELS.CAVEAT, err)
            if "".join([str(i) for i in err.args]) == "timed out":
                BuiltinVariables["timed_out"] = True
                return True
            return False
        except Exception as err:
            LOG_CATEGORIES.PYTHON_EXCEPTION(LOG_LEVELS.CAVEAT, err)
            exit(-1)
        BuiltinVariables["timed_out"] = False
        return True

    def Check(self) -> bool:
        try:
            if type(self.check) != str:
                raise Exception("The type of 'check' must be a string!")
            UserGlobals.update(BuiltinVariables)
            UserGlobals.update(QueryAllVariables())
            ret = eval(self.check, UserGlobals)
            try:
                BuiltinVariables["url_response"].close()
            except:
                pass
        except PyFileException as e:
            LOG_CATEGORIES.NOT_EXISTS(LOG_LEVELS.ERROR, *e.args)
            exit(-1)
        except Exception as e:
            LOG_CATEGORIES.PYTHON_EXCEPTION(LOG_LEVELS.ERROR, e)
            raise Exception()
        return bool(ret)

    def Run(self) -> bool:
        LOG_CATEGORIES.TARGET_IS_RUNNING(LOG_LEVELS.INFO, self.name)
        i = self.retry
        while i > 0:
            if self.Request():
                status = self.Check()
            else:
                status = False
            if status:
                break
            i -= 1
            if not i:
                break
            LOG_CATEGORIES.TARGET_RETRY(LOG_LEVELS.CAVEAT, self.name, self.retry - i)
            try:
                if "retry_interval" in self.target_info:
                    time.sleep(float(self.target_info["retry_interval"]) / 1000)
                else:
                    time.sleep(float(CONF.retry_interval) / 1000)
            except:
                pass
        return status

class IFsInquiry:
    def __init__(self):
        def getWid(s):
            return len(str(s))
        infos = InterfacesInfo.GetInterfacesInfo()
        # 取带 IPv4 地址的网卡, 地址取第一个.
        self.infos = []
        self.fields = ["Index", "Name", "Friendly name", "IP address", "MAC address"]
        self.fieldsWidth = [len(i) for i in self.fields]
        for i in infos:
            # 五元组 (索引, 名称, 友好名称, IP 地址, 物理地址)
            item = [str(i["index"]), i["adapter_name"], i["friendly_name"], None, i["mac"]]
            for o in i["addresses"]:
                if o["address_family"] == "AF_INET":
                    item[3] = o["address"]
                    break
            if item[3]:
                for idx, val in enumerate(item):
                    self.fieldsWidth[idx] = max(getWid(val), self.fieldsWidth[idx])
                self.infos.append(item)

    def __str__(self):
        def esp(s):
            s = s.replace("<<", "{")
            s = s.replace(">>", "}")
            return s
        ret = []
        divLine = "+" + "+".join(["-" * wid for wid in self.fieldsWidth]) + "+" + "\n"
        titleLine = "|" + ("|".join(["<<: ^{}>>"] * 5)).format(*self.fieldsWidth) + "|" + "\n"
        titleLine = esp(titleLine).format(*self.fields)
        valueLineTemplate = "|" + ("|".join(["<<: >{}>>"] * 5)).format(*self.fieldsWidth) + "|" + "\n"
        ret.append(divLine)
        ret.append(titleLine)
        for i in self.infos:
            ret.append(divLine)
            ret.append(esp(valueLineTemplate).format(*i))
        ret.append(divLine)
        return "\n" + "".join(ret)

    def FindInterface(self, keyword):
        # 按列找
        tInfos = zip(*self.infos)
        isFind = False
        for i in tInfos:
            try:
                idx = i.index(keyword)
                isFind = True
                break
            except:
                continue
        if isFind:
            return self.infos[idx]
        raise Exception(keyword)


def load_config(filename):
    global CONF
    # 配置文件
    CONF = ConfigManager(filename)

    # 加载配置到配置变量
    try:
        variables = CONF.variables
        UserVariables.update(variables)
    except Exception as e:
        LOG_CATEGORIES.CONFIG_PROP_NOT_FOUND(LOG_LEVELS.INFO, e.args[1])
    # 加载目标配置
    try:
        global Targets
        Targets = CONF.targets
        for tar in Targets:
            Targets[tar] = Target(tar, Targets[tar])
    except Exception as e:
        LOG_CATEGORIES.CONFIG_PROP_NOT_FOUND(LOG_LEVELS.ERROR, e.args[1])
        exit(-1)
    try:
        global StartingTarget
        # 检查运行选项中是否指定了目标
        if Options["-t"]:
            StartingTarget = Options["-t"][0]
        else:
            StartingTarget = CONF.default_target
    except Exception as e:
        LOG_CATEGORIES.CONFIG_PROP_NOT_FOUND(LOG_LEVELS.INFO, e.args[1])
    # 加载需认证网卡配置
    try:
        global ProcessIfs
        # 检查是否在参数指定接口
        if Options["-I"]:
            ProcessIfs = Options["-I"][0].split(",")
        else:
            ProcessIfs = CONF.process_ifs
    except Exception as e:
        LOG_CATEGORIES.CONFIG_PROP_NOT_FOUND(LOG_LEVELS.ERROR, e.args[1])
        LOG_CATEGORIES.AVAILABLE_INTERFACES(LOG_LEVELS.INFO, Interfaces)
        exit(-1)
    UpdateInterfacesInfo()

    # 用户的全局空间
    global UserGlobals, PyFileException
    UserGlobals = {}

    class PyFileException(Exception):
        pass

    # 给用户的函数
    def loadpy(filename):
        gb = {}
        lo = {}
        class dotaccess:
            def __getattr__(self, name: str):
                if name not in UserGlobals:
                    raise PyFileException("loadpy", name, filename)
                return UserGlobals[name]
        path = CONF.GetFilePath()
        absFilePath = os.path.join(path, filename)
        if not os.path.exists(absFilePath):
            raise PyFileException("loadpy", filename, path)
        with open(absFilePath, "r", encoding="utf8") as f:
            pytext = f.read()
        exec(pytext, UserGlobals)
        return dotaccess()

    UserGlobals["loadpy"] = loadpy

def UpdateInterfacesInfo():
    Interfaces = IFsInquiry()
    # 查找网卡配置对应接口五元组信息
    try:
        BuiltinVariables["all_ifs"] = {i:Interfaces.FindInterface(i) for i in ProcessIfs}
    except Exception as e:
        LOG_CATEGORIES.INTERFACE_NOT_FOUND(LOG_LEVELS.ERROR, e.args[0])
        LOG_CATEGORIES.AVAILABLE_INTERFACES(LOG_LEVELS.INFO, Interfaces)
        exit(-1)

def process():
    for ifName in ProcessIfs:
        ifInfo = BuiltinVariables["all_ifs"][ifName]
        showName = ifInfo[1] if ifInfo[2] == "" else ifInfo[2]
        LOG_CATEGORIES.PROCESSING(LOG_LEVELS.INFO, "interface", f"{showName} ({ifInfo[3]})")

        continue_next = True
        BuiltinVariables["next_target"] = StartingTarget
        while continue_next and BuiltinVariables["next_target"]:
            # 更新当前接口地址信息
            UpdateInterfacesInfo()
            ifInfo = BuiltinVariables["all_ifs"][ifName]
            BuiltinVariables["if_mac"] = ifInfo[4]
            BuiltinVariables["if_ip"] = ifInfo[3]
            UpdateRequester(BuiltinVariables["if_ip"])
            # 确认有这个目标
            try:
                target = BuiltinVariables["next_target"]
                target = Targets[target]
            except:
                LOG_CATEGORIES.TARGET_NOT_FOUND(LOG_LEVELS.ERROR, BuiltinVariables["next_target"])
                exit(-1)
            # 目标变量更新, 执行目标
            try:
                BuiltinVariables["current_target"] = BuiltinVariables["next_target"]
                BuiltinVariables["next_target"] = target.next
                status = target.Run()
                if not status:
                    LOG_CATEGORIES.TARGET_FAILURE(LOG_LEVELS.CAVEAT, target.name)
                    continue_next = False
                else:
                    LOG_CATEGORIES.TARGET_SUCCESSFUL(LOG_LEVELS.INFO, target.name)
                    continue_next = True
            except:
                LOG_CATEGORIES.TARGET_FAILURE(LOG_LEVELS.CAVEAT, target.name)
                continue_next = False

def parse_run_args():
    options = {
        "-c": 1, # 指定配置文件
        "-I": 1, # 指定接口列表, 逗号分隔
        "-i": 0, # 列出所有可用接口
        "-l": 0, # 列出所有目标
        "-t": 1  # 指定执行目标
    }

    curOpt = ""
    optArgs = []
    def renew_option():
        if None in optArgs:
            LOG_CATEGORIES.TOO_FEW_PARAMETER(LOG_LEVELS.ERROR, curOpt)
            exit(-1)
        if optArgs:
            options[curOpt] = optArgs
    for i in sys.argv:
        if optArgs and optArgs[0] == None:
            optArgs.pop(0)
            optArgs.append(i)
        elif i in options:
            renew_option()
            curOpt = i
            if options[curOpt]:
                optArgs = [None] * options[curOpt]
            else:
                options[curOpt] = True
                optArgs = []
        else:
            if curOpt:
                LOG_CATEGORIES.UNKNOWN_OPTION(LOG_LEVELS.ERROR, curOpt)
                exit(-1)
    renew_option()
    for i in options:
        if type(options[i]) == int:
            options[i] = False
    global Options
    Options = options

if __name__ == "__main__":
    global Interfaces
    Interfaces = IFsInquiry()
    parse_run_args()
    # 检查显示接口参数
    if Options["-i"]:
        print(Interfaces)
        exit(0)
    # 检查配置文件参数
    if Options["-c"]:
        configName:str = Options["-c"][0]
        if not configName.endswith(".json") and not configName.endswith(".json"):
            LOG_CATEGORIES.CONFIG_FILE_SUFFIX_ERROR(LOG_LEVELS.ERROR)
            exit(-1)
        load_config(configName)
    else:
        LOG_CATEGORIES.LOAD_DEFAULT(LOG_LEVELS.INFO, "config file", "default_config.json")
        load_config("default_config.json")
    # 检查是否列出所有目标
    if Options["-l"]:
        for i in Targets:
            print(i)
        exit(0)
    # 进行处理
    process()


