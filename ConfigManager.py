import os, sys
import json
from typing import Any, Iterable

class ConfigManager:
    _INTERNAL = ["_config", "_path", "config_file"]

    def __init__(self, config_file = "config.json") -> None:
        self._config = {}
        self.config_file = config_file
        try:
            self._path = os.path.split(os.path.realpath(sys.argv[0]))[0]
            with open(os.path.join(self._path, self.config_file), "r", encoding="utf-8") as f:
                config = json.load(f)
            if type(self._config) != dict:
                config = {}
        except Exception:
            config = {}
        self._config.update(config)

    def __getattr__(self, name: str) -> Any:
        try:
            # 获取初始内部属性, 如果失败则从 config 里获取
            if name in vars(self): # vars(self) 同 self.__dict__
                return vars(self)[name]
            if name in vars(ConfigManager):
                return vars(ConfigManager)[name]
            return self._config[name]
        except:
            raise AttributeError(f"No attr named: {name}", name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ConfigManager._INTERNAL:
            # super.__setattr__(self, name, value)
            self.__dict__[name] = value
        else:
            # 内部成员参数之外的写入均当作配置参数
            try:
                self._config[name] = value
                if (not os.path.exists(self._path)):
                    os.makedirs(self._path)
                with open(os.path.join(self._path, self.config_file), "w", encoding="utf-8") as f:
                    json.dump(self._config, f, ensure_ascii=False, indent=4)
            except:
                raise AttributeError(f"Could not update {self.config_file} on : {self._path}")

    def __delattr__(self, name: str) -> None:
        if name in ConfigManager._INTERNAL:
            raise AttributeError("No way!")
        else:
            # 内部成员参数之外均当作配置参数删除
            try:
                del self._config[name]
                if (not os.path.exists(self._path)):
                    os.makedirs(self._path)
                with open(os.path.join(self._path, self.config_file), "w", encoding="utf-8") as f:
                    json.dump(self._config, f, ensure_ascii=False, indent=4)
            except:
                raise AttributeError(f"Could not update config.json on : {self._path}")

    def __dir__(self) -> Iterable[str]:
        return (*self.__dict__, *self._config)

    def GetFilePath(self) -> str:
        return self._path
