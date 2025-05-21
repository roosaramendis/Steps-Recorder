// SS_ServerApp.cpp : This file contains the 'main' function. Program execution begins and ends there.
//
#include <iostream>
#include <thread>
#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <algorithm>
#include <codecvt>
#include <locale>
#include <windows.h>
#include <gdiplus.h>

using namespace Gdiplus;

#pragma comment(lib, "Gdiplus.lib")

template <typename T>
T clamp(T val, T minVal, T maxVal) {
    return (val < minVal) ? minVal : (val > maxVal) ? maxVal : val;
}

HWND getWindow_from_windowName(const std::string& windowName_str) {
    // Convert UTF-8 std::string to std::wstring (UTF-16)
    std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> converter;
    std::wstring windowName_wstr = converter.from_bytes(windowName_str);

    // Find the window with the exact title
    HWND hwnd = FindWindowW(NULL, windowName_wstr.c_str());

    return hwnd; // nullptr if not found
}

int get_encoder_clsid(const WCHAR* format, CLSID* pClsid) {
    UINT num = 0;
    UINT size = 0;

    GetImageEncodersSize(&num, &size);
    if (size == 0) return -1;

    std::vector<BYTE> buffer(size);
    ImageCodecInfo* pImageCodecInfo = (ImageCodecInfo*)buffer.data();
    GetImageEncoders(num, size, pImageCodecInfo);

    for (UINT i = 0; i < num; ++i) {
        if (wcscmp(pImageCodecInfo[i].MimeType, format) == 0) {
            *pClsid = pImageCodecInfo[i].Clsid;
            return i;
        }
    }
    return -1;
}

bool save_image_gdiplus(const std::string& filename, HBITMAP hBitmap, const std::string& format, int quality) {
    Bitmap bmp(hBitmap, NULL);
    CLSID encoderClsid;
    const WCHAR* mime;

    if (format == "png") {
        mime = L"image/png";
    }
    else if (format == "jpg" || format == "jpeg") {
        mime = L"image/jpeg";
    }
    else {
        return false;
    }

    if (get_encoder_clsid(mime, &encoderClsid) < 0) return false;

    std::wstring wfilename(filename.begin(), filename.end());

    EncoderParameters encoderParams;
    encoderParams.Count = 1;

    if (format == "jpg" || format == "jpeg") {
        encoderParams.Parameter[0].Guid = EncoderQuality;
        encoderParams.Parameter[0].Type = EncoderParameterValueTypeLong;
        encoderParams.Parameter[0].NumberOfValues = 1;
        ULONG q = clamp(quality, 0, 100);
        encoderParams.Parameter[0].Value = &q;

        return bmp.Save(wfilename.c_str(), &encoderClsid, &encoderParams) == Ok;
    }
    else {
        return bmp.Save(wfilename.c_str(), &encoderClsid, NULL) == Ok;
    }
}

bool take_screenshot(const std::string& filename, const std::string& format, int quality, int captureWindow, HWND hwnd) {
    if (captureWindow == 1) {
        if (!hwnd) {
            std::cerr << "[ERR from CPP] Window not found\n";
            return false;
        }
        RECT rc;
        GetClientRect(hwnd, &rc);
        int width = rc.right - rc.left;
        int height = rc.bottom - rc.top;

        HDC hWindow = GetDC(hwnd);
        HDC hMemDC = CreateCompatibleDC(hWindow);

        HBITMAP hBitmap = CreateCompatibleBitmap(hWindow, width, height);
        SelectObject(hMemDC, hBitmap);
        BitBlt(hMemDC, 0, 0, width, height, hWindow, 0, 0, SRCCOPY);

        bool result = save_image_gdiplus(filename, hBitmap, format, quality);

        DeleteObject(hBitmap);
        DeleteDC(hMemDC);
        ReleaseDC(NULL, hWindow);
        return result;
    }
    else if (captureWindow == 0) {
        HDC hScreenDC = GetDC(NULL);
        int width = GetSystemMetrics(SM_CXSCREEN);
        int height = GetSystemMetrics(SM_CYSCREEN);

        HDC hMemDC = CreateCompatibleDC(hScreenDC);
        HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, width, height);
        SelectObject(hMemDC, hBitmap);

        BitBlt(hMemDC, 0, 0, width, height, hScreenDC, 0, 0, SRCCOPY);

        bool result = save_image_gdiplus(filename, hBitmap, format, quality);

        DeleteObject(hBitmap);
        DeleteDC(hMemDC);
        ReleaseDC(NULL, hScreenDC);
        return result;
    }

    return false;
}

void process_command(const std::string& msg) {
    // message format:
    // "SS|filepath|format|quality|captureWindow(0 or 1)|windowName"
    if (msg.rfind("SS|", 0) == 0) {
        std::stringstream ss(msg.substr(3));
        std::string filepath, format, qlty_str, onlyWindow_str, windowName_str;

        std::getline(ss, filepath, '|');
        std::getline(ss, format, '|');
        std::getline(ss, qlty_str, '|');
        std::getline(ss, onlyWindow_str, '|');
        std::getline(ss, windowName_str);

        int quality = std::stoi(qlty_str);
        int captureWindow = std::stoi(onlyWindow_str);
        HWND hwnd = getWindow_from_windowName(windowName_str);

        if (take_screenshot(filepath, format, quality, captureWindow, hwnd)) {
            std::cout << "[OK from CPP] Saved screenshot to " << filepath << "\n";
        }
        else {
            std::cerr << "[ERR from CPP] Failed to save screenshot\n";
        }
    }
    else if (msg == "exit") {
        std::cout << "[INFO from CPP] Exit command received. Shutting down.\n";
        exit(0);
    }
    else {
        std::cerr << "[ERR from CPP] Unknown command: " << msg << "\n";
    }
}

int main() {
    // Initialize GDI+
    ULONG_PTR gdiplusToken;
    GdiplusStartupInput gdiplusStartupInput;
    GdiplusStartup(&gdiplusToken, &gdiplusStartupInput, nullptr);

    std::cout << "[INFO from CPP] Screenshot stdin server started. Waiting for commands...\n";

    std::string line;
    while (true) {
        std::cout << "[CPP] Waiting for command...\n";
        if (!std::getline(std::cin, line)) {
            std::cout << "[INFO from CPP] error \n";
            // EOF or input error
            break;
        }
        std::cout << "[CPP] Received line: " << line << "\n";
        if (line.empty())
            continue;
        process_command(line);
    }

    // Shutdown GDI+
    GdiplusShutdown(gdiplusToken);

    return 0;
}