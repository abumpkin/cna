#include "winif.h"
#include <cJSON.h>
#include <cJSON_Utils.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <base64.h>

// 相关信息:
// https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/
// Management Information Base (MIB)
// GetAdaptersAddresses: 查接口名和地址信息
// GetIfEntry2: 查接口流量信息
// GetIfTable: 简要信息

char addrOutBuffer[UNIT_BUFLEN];

// 返回 0 表示成功, 非 0 成功.
int __cdecl GetInfos(char *out, ULONG len) {
    ULONG flags = GAA_FLAG_INCLUDE_PREFIX; // | GAA_FLAG_INCLUDE_ALL_INTERFACES;
    ULONG family = AF_UNSPEC;

    PIP_ADAPTER_ADDRESSES pCurrAddresses = NULL;
    PIP_ADAPTER_UNICAST_ADDRESS pUnicast = NULL;
    PIP_ADAPTER_ANYCAST_ADDRESS pAnycast = NULL;
    PIP_ADAPTER_MULTICAST_ADDRESS pMulticast = NULL;
    IP_ADAPTER_DNS_SERVER_ADDRESS *pDnServer = NULL;
    IP_ADAPTER_PREFIX *pPrefix = NULL;

    PIP_ADAPTER_ADDRESSES pAddresses = NULL;
    ULONG outBufLen = 0;
    ULONG Iterations = 1;
    DWORD dwSize = 0;
    DWORD dwRetVal = 0;

    for (; Iterations <= MAX_MULTIPLIER; Iterations++) {
        outBufLen = Iterations * UNIT_BUFLEN;
        pAddresses = (IP_ADAPTER_ADDRESSES *) MALLOC(outBufLen);
        if (pAddresses == NULL) {
            return 0;
        }
        dwRetVal = GetAdaptersAddresses(family, flags, NULL,
            pAddresses, &outBufLen);
        if (dwRetVal == ERROR_BUFFER_OVERFLOW) {
            FREE(pAddresses);
            pAddresses = NULL;
            continue;
        }
        break;
    }
    if (dwRetVal != NO_ERROR) {
        return 0;
    }
    // 转码缓冲区
    char *encodeBuf;
    // json
    cJSON *jsonRoot = cJSON_CreateArray();
    pCurrAddresses = pAddresses;
    while(pCurrAddresses) {
        cJSON *ifInfo = cJSON_CreateObject();
        cJSON_AddItemToArray(jsonRoot, ifInfo);
        cJSON *index = cJSON_CreateNumber(pCurrAddresses->IfIndex);
        cJSON *adapterName = cJSON_CreateString(pCurrAddresses->AdapterName);
        // printf("%s\n", pCurrAddresses->AdapterName);
        // 获取友好名称
        ULONG nameLen = wcslen(pCurrAddresses->FriendlyName) * sizeof(WCHAR);
        ULONGLONG encodeBufLen = BASE64_ENCODE_OUT_SIZE(nameLen);
        encodeBuf = MALLOC(encodeBufLen);
        base64_encode((UCHAR*) pCurrAddresses->FriendlyName, nameLen, encodeBuf);
        cJSON *friendlyName = cJSON_CreateString(encodeBuf);
        FREE(encodeBuf);
        // printf("%s\n", encodeBuf);
        // 网络 GUID
        char szBuf[64];
        sprintf_s(szBuf, 64, "{%08x-%04x-%04x-%02X%02X-%02X%02X%02X%02X%02X%02X}",
            pCurrAddresses->NetworkGuid.Data1, pCurrAddresses->NetworkGuid.Data2,
            pCurrAddresses->NetworkGuid.Data3,
            pCurrAddresses->NetworkGuid.Data4[0], pCurrAddresses->NetworkGuid.Data4[1],
            pCurrAddresses->NetworkGuid.Data4[2], pCurrAddresses->NetworkGuid.Data4[3],
            pCurrAddresses->NetworkGuid.Data4[4], pCurrAddresses->NetworkGuid.Data4[5],
            pCurrAddresses->NetworkGuid.Data4[6], pCurrAddresses->NetworkGuid.Data4[7]);
        cJSON *networkGUID = cJSON_CreateString(szBuf);
        // MAC 地址
        szBuf[0] = 0;
        if (pCurrAddresses->PhysicalAddressLength >= 6) {
            sprintf_s(szBuf, 64, "%02x-%02x-%02x-%02x-%02x-%02x",
                pCurrAddresses->PhysicalAddress[0],
                pCurrAddresses->PhysicalAddress[1],
                pCurrAddresses->PhysicalAddress[2],
                pCurrAddresses->PhysicalAddress[3],
                pCurrAddresses->PhysicalAddress[4],
                pCurrAddresses->PhysicalAddress[5]);
        }
        cJSON *mac = cJSON_CreateString(szBuf);
        // printf("%s\n", szBuf);
        cJSON_AddItemToObject(ifInfo, "index", index);
        cJSON_AddItemToObject(ifInfo, "adapter_name", adapterName);
        cJSON_AddItemToObject(ifInfo, "friendly_name_base64", friendlyName);
        cJSON_AddItemToObject(ifInfo, "network_guid", networkGUID);
        cJSON_AddItemToObject(ifInfo, "mac", mac);

        pUnicast = pCurrAddresses->FirstUnicastAddress;
        cJSON *unicasts = cJSON_CreateArray();
        cJSON_AddItemToObject(ifInfo, "unicasts", unicasts);
        while (pUnicast) {
            cJSON *unicast = cJSON_CreateObject();
            cJSON_AddItemToArray(unicasts, unicast);
            PSOCKADDR pAddr = pUnicast->Address.lpSockaddr;
            USHORT family = pAddr->sa_family;
            cJSON *addressFamily = cJSON_CreateString(AF_FAMILY[family]);
            // 获取地址
            DWORD outLen = UNIT_BUFLEN;
            dwRetVal = WSAAddressToStringA(pAddr, pUnicast->Address.iSockaddrLength, NULL,
                addrOutBuffer, &outLen);
            cJSON *addr = cJSON_CreateString("");
            if (dwRetVal == NO_ERROR) {
                cJSON_Delete(addr);
                addr = cJSON_CreateString(addrOutBuffer);
            }
            cJSON *maskLen = cJSON_CreateNumber(pUnicast->OnLinkPrefixLength);

            cJSON_AddItemToObject(unicast, "address_family", addressFamily);
            cJSON_AddItemToObject(unicast, "address", addr);
            cJSON_AddItemToObject(unicast, "mask_len", maskLen);
            pUnicast = pUnicast->Next;
        }
        pCurrAddresses = pCurrAddresses->Next;
    }
    char *jsonText = cJSON_PrintUnformatted(jsonRoot);
    ULONG jsonLen = strlen(jsonText);
    if (jsonLen > len) {
        return 0;
    }
    memcpy(out, jsonText, jsonLen);
    cJSON_Delete(jsonRoot);
    return jsonLen;
}