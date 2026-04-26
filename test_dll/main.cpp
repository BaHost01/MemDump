#include <windows.h>
#include <stdio.h>

DWORD WINAPI HeartbeatThread(LPVOID lpParam) {
    HMODULE hModule = (HMODULE)lpParam;
    while (TRUE) {
        char buffer[128];
        sprintf(buffer, "MemDump Heartbeat: DLL [0x%p] is alive and running.\n", hModule);
        OutputDebugStringA(buffer);
        Sleep(5000); // Wait 5 seconds
    }
    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule,
                       DWORD  ul_reason_for_call,
                       LPVOID lpReserved
                     )
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
    {
        char message[256];
        sprintf(message, "MemDump: DLL Attached Successfully!\nBase Address: 0x%p\n\nA background heartbeat thread has been started.", hModule);
        MessageBoxA(NULL, message, "Injection Success", MB_OK | MB_ICONINFORMATION);
        
        // Start a background thread to show persistent execution
        CreateThread(NULL, 0, HeartbeatThread, hModule, 0, NULL);
        break;
    }
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}
