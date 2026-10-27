import os
import platform


def detect():
    return {
        "system": platform.system(),
        "release": platform.release(),
        "cpu_cores": os.cpu_count(),
    }


if __name__ == "__main__":
    for k, v in detect().items():
        print(f"{k:12} {v}")
