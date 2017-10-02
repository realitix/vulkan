#ifndef _FAKE_TYPEDEFS_H
#define _FAKE_TYPEDEFS_H

/* Xlib objects */
typedef struct Display Display;
typedef unsigned long XID;
typedef unsigned long VisualID;
typedef XID Window;

/* Mir typedefs */
typedef void* MirEGLNativeWindowType;
typedef void* MirEGLNativeDisplayType;
typedef struct MirConnection MirConnection;
typedef struct MirSurface MirSurface;
typedef struct MirSurfaceSpec MirSurfaceSpec;
typedef struct MirScreencast MirScreencast;
typedef struct MirPromptSession MirPromptSession;
typedef struct MirBufferStream MirBufferStream;
typedef struct MirPersistentId MirPersistentId;
typedef struct MirBlob MirBlob;
typedef struct MirDisplayConfig MirDisplayConfig;

/* xcb typedefs */
typedef struct xcb_connection_t xcb_connection_t;
typedef uint32_t xcb_window_t;
typedef uint32_t xcb_visualid_t;

/* android */
typedef struct ANativeWindow ANativeWindow;

/* windows */
typedef void *PVOID;
typedef PVOID HANDLE;
typedef HANDLE HINSTANCE;
typedef HANDLE HWND;
typedef unsigned long DWORD;
typedef void *LPVOID;
typedef wchar_t WCHAR;
typedef const WCHAR *LPCWSTR;

typedef struct _SECURITY_ATTRIBUTES {
    DWORD  nLength;
    LPVOID lpSecurityDescriptor;
    int   bInheritHandle;
} SECURITY_ATTRIBUTES, *PSECURITY_ATTRIBUTES, *LPSECURITY_ATTRIBUTES;

#endif
