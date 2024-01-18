import sys, time

class LOG_LEVELS:
    class LOG_LEVEL:
        def __init__(self, prefix, stream):
            self.prefix = prefix
            self.stream = stream
    INFO = LOG_LEVEL("[INFO] ", sys.stdout)
    CAVEAT = LOG_LEVEL("[CAVEAT] ", sys.stdout)
    ERROR = LOG_LEVEL("[ERROR] ", sys.stderr)

class LogHandler:

    def __init__(self, log_stream: bool = True, log_file: str = ""):
        """创建 Log 处理对象

        Args:
            log_stream (bool, optional): 是否输出到命令行界面. Defaults to True.
            log_file (str, optional): 写入到日志文件文件名, 空字符串则不写入. Defaults to "".
        """
        class _LOG_CATEGORIES:
            def TIMEOUT_NOT_SET(level, defaultTimeout): return \
                self.handler(level, f"Default connect timeout is '{defaultTimeout}'.")
            def PYTHON_EXCEPTION(level, e:Exception): return \
                self.handler(level, " ".join([str(i) for i in e.args]))
            def CONFIG_PROP_NOT_FOUND(level, prop): return \
                self.handler(level,
                             f"Not found '{prop}' in the configuration file.")
            def VARIABLE_NOT_ALLOWED(level, prop): return \
                self.handler(level,
                             f"The variable name '{prop}' is not allowed.")
            def VARIABLE_BUILTIN_NOT_FOUND(level, varname, builtinVarname): return \
                self.handler(level,
                             f"No built-in variable called '{builtinVarname}' as to "
                             f"mapping this to the variable '{varname}'.")
            def CONFIG_TARGET_PROP_NOT_FOUND(level, Target_name, prop): return \
                self.handler(level,
                             f"Not found '{prop}' in the '{Target_name}' Target.")
            def HTTP_METHOD_UNKNOWN(level, Target_name, method): return \
                self.handler(level, f"Unknown http '{method}' method in '{Target_name}'. Only support 'GET' and 'POST'.")
            def URL_NOT_VALID(level, Target_name, url): return \
                self.handler(level, f"The url '{url}' in the '{Target_name}' Target is not valid.")
            def TARGET_IS_RUNNING(level, Target_name): return \
                self.handler(level, f"Running '{Target_name}' Target...")
            def TARGET_RESPONSE_CODE(level, Target_name, code): return \
                self.handler(level, f"The '{Target_name}' Target response with status code {code}.")
            def REQUEST_REDIRECT(level, code, msg):
                self.handler(level, f"Request happens redirect with code {code} ({msg}).")
            def TARGET_RETRY(level, Target_name, times):
                self.handler(level, f"Retry {times} times for Target '{Target_name}'.")
            def TARGET_FAILURE(level, Target_name):
                self.handler(level, f"The '{Target_name}' Target failed.")
            def TARGET_SUCCESSFUL(level, Target_name):
                self.handler(level, f"The '{Target_name}' Target successful.")
            def TARGET_NO_METHOD_MATCHED(level, Target_name):
                self.handler(level, f"Target '{Target_name}' has no method matched and will just simply do check.")
            def INTERFACE_NOT_FOUND(level, keyword):
                self.handler(level, f"Interface '{keyword}' is not found.")
            def AVAILABLE_INTERFACES(level, available):
                self.handler(level, f"Available interfaces as follow listed:{available}")
            def PROCESSING(level, what, obj):
                self.handler(level, f"Now processing {what} '{obj}'...")
            def UNKNOWN_OPTION(level, option):
                self.handler(level, f"Unknown option '{option}'.")
            def TOO_FEW_PARAMETER(level, option):
                self.handler(level, f"Too few parameters for option '{option}'.")
            def CONFIG_FILE_SUFFIX_ERROR(level):
                self.handler(level, f"The config file name must be a .json file.")
            def LOAD_DEFAULT(level, what, val):
                self.handler(level, f"Load default {what}: '{val}'")
            def TARGET_NOT_FOUND(level, tar):
                self.handler(level, f"Not found the target '{tar}'.")
            def NOT_EXISTS(level, what, things, path):
                self.handler(level, f"{what}: '{things}' not exists in '{path}'.")


        self.LOG_CATEGORIES = _LOG_CATEGORIES
        self.log_to_stream = log_stream
        self.log_to_file = log_file

    def handler(self, level, info):
        curtime = "[{}]".format(time.strftime("%Y-%m-%d %H:%M:%S %z", time.gmtime()))
        log_info = curtime + level.prefix + info
        if self.log_to_stream:
            level.stream.write(log_info)
            level.stream.write("\n")
        if self.log_to_file != "":
            with open(self.log_to_file, "wa") as f:
                f.write(log_info)
                f.write("\n")
