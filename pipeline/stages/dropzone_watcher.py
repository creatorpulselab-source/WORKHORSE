import time
import sys
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.dropzone_fulfiller import DropzoneFulfiller

def run_watcher():
    print("[DROPZONE WATCHER] Active and monitoring F:\\WORKHORSE\\dropzone...")
    fulfiller = DropzoneFulfiller()
    while True:
        try:
            results = fulfiller.process_dropzone()
            if results:
                for r in results:
                    name = r.get('order_name')
                    count = r.get('photos_processed')
                    print(f"[DROPZONE WATCHER] Completed order: {name} ({count} photos)")
        except Exception as e:
            print(f"[DROPZONE WATCHER ERROR] {e}")
        time.sleep(3)

if __name__ == "__main__":
    run_watcher()
