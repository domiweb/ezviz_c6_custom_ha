import ctypes
import os
import time
import atexit
from flask import Flask, jsonify

SDK_ROOT = os.environ.get("SDK_ROOT", "/app/sdk")
CAMERA_IP = os.environ["CAMERA_IP"].encode()
CAMERA_PORT = int(os.environ.get("CAMERA_PORT", "8000"))
USERNAME = os.environ["CAMERA_USERNAME"].encode()
PASSWORD = os.environ["CAMERA_PASSWORD"].encode()
CHANNEL = int(os.environ.get("CAMERA_CHANNEL", "1"))
DEFAULT_SPEED = int(os.environ.get("CAMERA_SPEED", "7"))
DEFAULT_DURATION = float(os.environ.get("CAMERA_DURATION", "0.15"))

# Passe diese Dateinamen an dein Linux-SDK an, falls sie bei dir anders heißen.
SDK_PATH = os.path.join(SDK_ROOT, "libhcnetsdk.so")
CRYPTO_CANDIDATES = [
    "libcrypto.so.1.1",
    "libcrypto.so",
    "libcrypto.so.3",
]
SSL_CANDIDATES = [
    "libssl.so.1.1",
    "libssl.so",
    "libssl.so.3",
]

sdk = ctypes.cdll.LoadLibrary(SDK_PATH)


class NET_DVR_DEVICEINFO_V30(ctypes.Structure):
    _fields_ = [
        ("sSerialNumber", ctypes.c_ubyte * 48),
        ("byAlarmInPortNum", ctypes.c_ubyte),
        ("byAlarmOutPortNum", ctypes.c_ubyte),
        ("byDiskNum", ctypes.c_ubyte),
        ("byDVRType", ctypes.c_ubyte),
        ("byChanNum", ctypes.c_ubyte),
        ("byStartChan", ctypes.c_ubyte),
        ("byAudioChanNum", ctypes.c_ubyte),
        ("byIPChanNum", ctypes.c_ubyte),
        ("byRes1", ctypes.c_ubyte * 24),
    ]


class NET_DVR_DEVICEINFO_V40(ctypes.Structure):
    _fields_ = [
        ("struDeviceV30", NET_DVR_DEVICEINFO_V30),
        ("bySupportLock", ctypes.c_ubyte),
        ("byRetryLoginTime", ctypes.c_ubyte),
        ("byPasswordLevel", ctypes.c_ubyte),
        ("byProxyType", ctypes.c_ubyte),
        ("dwSurplusLockTime", ctypes.c_uint32),
        ("byCharEncodeType", ctypes.c_ubyte),
        ("bySupportDev5", ctypes.c_ubyte),
        ("bySupport", ctypes.c_ubyte),
        ("byLoginMode", ctypes.c_ubyte),
        ("dwOEMCode", ctypes.c_uint32),
        ("iResidualValidity", ctypes.c_int32),
        ("byResidualValidity", ctypes.c_ubyte),
        ("bySingleStartDTalkChan", ctypes.c_ubyte),
        ("bySingleDTalkChanNums", ctypes.c_ubyte),
        ("byPassWordResetLevel", ctypes.c_ubyte),
        ("byRes2", ctypes.c_ubyte * 84),
    ]


class NET_DVR_USER_LOGIN_INFO(ctypes.Structure):
    _fields_ = [
        ("sDeviceAddress", ctypes.c_char * 129),
        ("byUseTransport", ctypes.c_ubyte),
        ("wPort", ctypes.c_ushort),
        ("sUserName", ctypes.c_char * 64),
        ("sPassword", ctypes.c_char * 64),
        ("cbLoginResult", ctypes.c_void_p),
        ("pUser", ctypes.c_void_p),
        ("bUseAsynLogin", ctypes.c_bool),
        ("byProxyType", ctypes.c_ubyte),
        ("byUseUTCTime", ctypes.c_ubyte),
        ("byLoginMode", ctypes.c_ubyte),
        ("byHttps", ctypes.c_ubyte),
        ("iProxyID", ctypes.c_int32),
        ("byRes3", ctypes.c_ubyte * 120),
    ]


class NET_DVR_LOCAL_SDK_PATH(ctypes.Structure):
    _fields_ = [
        ("sPath", ctypes.c_char * 256),
    ]


sdk.NET_DVR_SetSDKInitCfg.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
sdk.NET_DVR_SetSDKInitCfg.restype = ctypes.c_bool

sdk.NET_DVR_Init.restype = ctypes.c_bool
sdk.NET_DVR_Cleanup.restype = ctypes.c_bool
sdk.NET_DVR_GetLastError.restype = ctypes.c_uint32
sdk.NET_DVR_SetConnectTime.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
sdk.NET_DVR_SetConnectTime.restype = ctypes.c_bool
sdk.NET_DVR_SetReconnect.argtypes = [ctypes.c_uint32, ctypes.c_bool]
sdk.NET_DVR_SetReconnect.restype = ctypes.c_bool
sdk.NET_DVR_Login_V40.argtypes = [
    ctypes.POINTER(NET_DVR_USER_LOGIN_INFO),
    ctypes.POINTER(NET_DVR_DEVICEINFO_V40),
]
sdk.NET_DVR_Login_V40.restype = ctypes.c_int32
sdk.NET_DVR_Logout.argtypes = [ctypes.c_int32]
sdk.NET_DVR_Logout.restype = ctypes.c_bool
sdk.NET_DVR_PTZControlWithSpeed_Other.argtypes = [
    ctypes.c_int32,
    ctypes.c_int32,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_uint32,
]
sdk.NET_DVR_PTZControlWithSpeed_Other.restype = ctypes.c_bool

TILT_UP = 21
TILT_DOWN = 22
PAN_LEFT = 23
PAN_RIGHT = 24

COMMANDS = {
    "left": PAN_LEFT,
    "right": PAN_RIGHT,
    "up": TILT_UP,
    "down": TILT_DOWN,
}


def err() -> int:
    return sdk.NET_DVR_GetLastError()


def first_existing_file(candidates):
    for name in candidates:
        path = os.path.join(SDK_ROOT, name)
        if os.path.exists(path):
            return path
    return None


def configure_sdk_paths():
    # 2 = HCNetSDKCom / Komponentenpfad auf Linux
    sdk_path_cfg = NET_DVR_LOCAL_SDK_PATH()
    component_path = os.path.join(SDK_ROOT, "HCNetSDKCom").encode()

    if len(component_path) >= 256:
        raise RuntimeError("HCNetSDKCom-Pfad ist zu lang")

    sdk_path_cfg.sPath = component_path
    ok_comp = sdk.NET_DVR_SetSDKInitCfg(2, ctypes.byref(sdk_path_cfg))

    crypto_path = first_existing_file(CRYPTO_CANDIDATES)
    ssl_path = first_existing_file(SSL_CANDIDATES)

    if crypto_path is None:
        raise RuntimeError(
            f"Keine OpenSSL-crypto-Bibliothek im sdk-Ordner gefunden. "
            f"Erwartet eine von: {CRYPTO_CANDIDATES}"
        )
    if ssl_path is None:
        raise RuntimeError(
            f"Keine OpenSSL-ssl-Bibliothek im sdk-Ordner gefunden. "
            f"Erwartet eine von: {SSL_CANDIDATES}"
        )

    crypto_buf = ctypes.create_string_buffer(crypto_path.encode())
    ssl_buf = ctypes.create_string_buffer(ssl_path.encode())

    ok_crypto = sdk.NET_DVR_SetSDKInitCfg(3, ctypes.cast(crypto_buf, ctypes.c_void_p))
    ok_ssl = sdk.NET_DVR_SetSDKInitCfg(4, ctypes.cast(ssl_buf, ctypes.c_void_p))

    print(
        f"SetSDKInitCfg: comp={ok_comp} crypto={ok_crypto} ssl={ok_ssl} "
        f"crypto_path={crypto_path} ssl_path={ssl_path}"
    )


def sdk_login() -> int:
    configure_sdk_paths()

    if not sdk.NET_DVR_Init():
        raise RuntimeError(f"NET_DVR_Init fehlgeschlagen: {err()}")

    sdk.NET_DVR_SetConnectTime(2000, 1)
    sdk.NET_DVR_SetReconnect(10000, True)

    info = NET_DVR_USER_LOGIN_INFO()
    info.sDeviceAddress = CAMERA_IP
    info.wPort = CAMERA_PORT
    info.sUserName = USERNAME
    info.sPassword = PASSWORD
    info.bUseAsynLogin = False

    dev = NET_DVR_DEVICEINFO_V40()
    user_id = sdk.NET_DVR_Login_V40(ctypes.byref(info), ctypes.byref(dev))
    if user_id < 0:
        raise RuntimeError(f"Login fehlgeschlagen: {err()}")

    print(
        f"Login erfolgreich: user_id={user_id}, "
        f"channels={dev.struDeviceV30.byChanNum}, "
        f"start_channel={dev.struDeviceV30.byStartChan}"
    )
    return user_id


USER_ID = sdk_login()


def cleanup():
    global USER_ID
    if USER_ID is not None:
        try:
            sdk.NET_DVR_Logout(USER_ID)
        except Exception:
            pass
        try:
            sdk.NET_DVR_Cleanup()
        except Exception:
            pass
        USER_ID = None


atexit.register(cleanup)

app = Flask(__name__)


def move(direction: str, speed: int = DEFAULT_SPEED, duration: float = DEFAULT_DURATION):
    cmd = COMMANDS[direction]
    ok = sdk.NET_DVR_PTZControlWithSpeed_Other(USER_ID, CHANNEL, cmd, 0, speed)
    if not ok:
        raise RuntimeError(f"PTZ START fehlgeschlagen: {err()}")
    time.sleep(duration)
    ok = sdk.NET_DVR_PTZControlWithSpeed_Other(USER_ID, CHANNEL, cmd, 1, speed)
    if not ok:
        raise RuntimeError(f"PTZ STOP fehlgeschlagen: {err()}")


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/left")
def left():
    move("left")
    return jsonify({"ok": True, "direction": "left"})


@app.post("/right")
def right():
    move("right")
    return jsonify({"ok": True, "direction": "right"})


@app.post("/up")
def up():
    move("up")
    return jsonify({"ok": True, "direction": "up"})


@app.post("/down")
def down():
    move("down")
    return jsonify({"ok": True, "direction": "down"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)