#pragma once
#define _WIN32_WINNT 0x0600
#include <winsock2.h>
#include <windows.h>
#include <iphlpapi.h>

#define API __declspec(dllexport)

#define UNIT_BUFLEN  5000
#define MAX_MULTIPLIER  20
#define MALLOC(x) HeapAlloc(GetProcessHeap(), 0, (x))
#define FREE(x) HeapFree(GetProcessHeap(), 0, (x))

const char *AF_FAMILY[] = {
    "AF_UNSPEC",
    "AF_UNIX",
    "AF_INET", // IPv4
    "AF_IMPLINK",
    "AF_PUP",
    "AF_CHAOS",
    "AF_NS",
    "AF_ISO",
    "AF_ECMA",
    "AF_DATAKIT",
    "AF_CCITT",
    "AF_SNA",
    "AF_DECnet",
    "AF_DLI",
    "AF_LAT",
    "AF_HYLINK",
    "AF_APPLETALK",
    "AF_NETBIOS",
    "AF_VOICEVIEW",
    "AF_FIREFOX",
    "AF_UNKNOWN1",
    "AF_BAN",
    "AF_ATM",
    "AF_INET6", // IPv6
    "AF_CLUSTER",
    "AF_12844",
    "AF_IRDA",
    "AF_NETDES",
    "AF_TCNPROCESS",
    "AF_TCNMESSAGE",
    "AF_ICLFXBM",
    "AF_BTH",
    "AF_MAX",
};
API int __cdecl GetInfos(char *out, ULONG len);
