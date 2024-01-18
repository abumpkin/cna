import platform
from ctypes import *
import json, base64, os

__all__ = ["GetInterfacesInfo"]

#### Windows ####

# https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getadaptersaddresses

BasicBufferSize = 5000
MaxBufferSizeMultiplier = 100

####  Linux  ####

family_map = {
    "inet": "AF_INET",
    "inet6": "AF_INET6"
}

#################

def GetInterfacesInfo():
    """获取 NIC 信息

    Returns:
        list:
            [
                {
                    "index": xxx,
                    "adapter_name": xxx,
                    "friendly_name": xxx,
                    "mac": xxx,
                    "addresses": [
                        {
                            "address_family": "AF_INET" | "AF_INET6",
                            "address": xxx,
                            "masklen": xxx
                        },
                        ...
                    ]
                },
                ...
            ]
    """
    ret = []
    if platform.system() == "Windows":
        winif = cdll.LoadLibrary("build/libwinif.dll")

        for i in range(1, MaxBufferSizeMultiplier + 1):
            # 实参
            retSize = c_uint32(BasicBufferSize * i)
            buffer = create_string_buffer(retSize.value)
            # 调用
            errorCode = winif.GetInfos(byref(buffer), retSize)
            if errorCode == 0:
                continue
            retSize.value = errorCode
            break

        # 出错返回空列表
        if errorCode == 0:
            return ret

        try:
            jsonText = buffer.raw.decode(encoding="ascii")
            strLen = jsonText.find("\0")
            if strLen != -1:
                jsonText = jsonText[:strLen]
            ifsInfo = json.loads(jsonText)
        except Exception as e:
            # 解析 JSON 信息出错
            return ret

        try:
            for i in ifsInfo:
                item = {}
                ret.append(item)
                item["index"] = i["index"]
                item["adapter_name"] = i["adapter_name"]
                item["friendly_name"] = base64.standard_b64decode(
                    i["friendly_name_base64"]).decode(encoding="utf-16-le")
                item["mac"] = i["mac"]
                item["addresses"] = i["unicasts"]
        except:
            return ret
    else:
        # LINUX
        with os.popen("ip -j -p addr", mode="r") as fp:
            jsonText = fp.read()
        try:
            ifsInfo = json.loads(jsonText)
        except:
            return ret
        for i in ifsInfo:
            item = {}
            ret.append(item)
            item["index"] = i["ifindex"]
            item["adapter_name"] = i["ifname"]
            item["friendly_name"] = ""
            if "ifalias" in i:
                item["friendly_name"] = i["ifalias"]
            item["mac"] = i["address"].replace(":", "-")
            item["addresses"] = []
            for o in i["addr_info"]:
                addr = {}
                item["addresses"].append(addr)
                addr["address_family"] = ""
                if o["family"] in family_map:
                    addr["address_family"] = family_map[o["family"]]
                addr["address"] = o["local"]
                addr["masklen"] = o["prefixlen"]
    return ret
