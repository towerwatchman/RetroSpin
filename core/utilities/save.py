#!/usr/bin/env python3
import os
import re
import sys
import time
import signal
import subprocess
import shutil

# Global state for cleanup
cdrdao_proc = None
toc_file = None
bin_file = None
err_log = "/tmp/retrospin_err.log"

def cleanup():
    global cdrdao_proc, toc_file, bin_file
    if cdrdao_proc and cdrdao_proc.poll() is None:
        print(f"Terminating cdrdao process {cdrdao_proc.pid}...")
        cdrdao_proc.terminate()
        try:
            cdrdao_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cdrdao_proc.kill()
            cdrdao_proc.wait()

    for path in [toc_file, bin_file]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                print(f"Removed partial file: {path}")
            except Exception as e:
                print(f"Failed to remove {path}: {e}")

import atexit
atexit.register(cleanup)

def _signal_handler(sig, frame):
    print(f"\nReceived signal {sig}, cleaning up...")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

def run_dialog(cmd, input_text=None):
    env = os.environ.copy()
    env["TERM"] = "linux"
    with open('/dev/tty', 'w') as tty, open(err_log, 'w') as err_f:
        proc = subprocess.run(cmd, env=env, input=input_text, text=True if input_text else False, stdout=tty, stderr=err_f, check=False)
    if os.path.exists(err_log) and os.path.getsize(err_log) > 0:
        with open(err_log, "r") as f:
            print(f"Dialog error: {f.read().strip()}")
        os.remove(err_log)
    return proc.returncode

def save_disc(drive_path, title, system):
    global cdrdao_proc, toc_file, bin_file

    USB_ROOT = "/media/usb0/games"
    if system == "psx":
        base_dir = f"{USB_ROOT}/PSX"
    elif system in ("mcd", "megacd"):
        base_dir = f"{USB_ROOT}/MegaCD"
    else:  # saturn
        base_dir = f"{USB_ROOT}/Saturn"

    for d in [f"{USB_ROOT}/PSX", f"{USB_ROOT}/Saturn", f"{USB_ROOT}/MegaCD"]:
        os.makedirs(d, exist_ok=True)

    cue_file = os.path.join(base_dir, f"{title}.cue")
    bin_file = os.path.join(base_dir, f"{title}.bin")
    toc_file = "/tmp/retrospin_temp.toc"

    # Delete toc file if exist at beginning
    for path in [toc_file]:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Removed existing temp file: {path}")
            except Exception as e:
                print(f"Failed to remove existing {path}: {e}")

    # Remove existing cue/bin
    for f in [cue_file, bin_file]:
        if os.path.exists(f):
            print(f"Removing existing file: {f}")
            os.remove(f)

    os.system("clear")

    # Prompt
    print("Executing dialog: Prompt to save disc")
    cmd = [
        "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
        "--yesno", f"Game file not found: {title}. Save disc as .bin/.cue to USB at {base_dir}?",
        "12", "50"
    ]
    response = run_dialog(cmd)
    print(f"Dialog exit status: {response}")
    if response != 0:
        print("User declined or dialog failed")
        return

    os.system("clear")

    # Show path
    cmd = [
        "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
        "--msgbox", f"Preparing to save disc to:\n{cue_file}\n{bin_file}", "12", "70"
    ]
    run_dialog(cmd)

    print(f"Preparing to save disc to: {cue_file}, {bin_file}...")

    # Find cdrdao
    ripdisc_path = "/usr/bin"
    cdrdao = shutil.which("cdrdao", path=ripdisc_path + ':' + os.environ.get('PATH', ''))
    if not cdrdao:
        msg = f"Error: cdrdao not found at {ripdisc_path}/cdrdao or in PATH"
        print(msg)
        cmd = [
            "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
            "--msgbox", msg, "12", "70"
        ]
        run_dialog(cmd)
        return

    # Comment out read-toc
    # print(f"Reading TOC data to detect disc size...")
    # toc_cmd = [cdrdao, "read-toc", "--driver", "generic-mmc-raw", "--device", drive_path, "--datafile", temp_datafile, toc_file]
    # toc_result = subprocess.run(toc_cmd)
    # if toc_result.returncode != 0:
    #     print(f"read-toc failed with status {toc_result.returncode}")
    #     final_message = "Failed to read TOC from disc."
    #     cmd = [
    #         "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
    #         "--msgbox", final_message, "12", "70"
    #     ]
    #     run_dialog(cmd)
    #     return

    # disc_sectors = None
    # if os.path.exists(toc_file):
    #     # To get leadout, we can run cdrdao show-toc or parse the toc file
    #     show_toc_cmd = [cdrdao, "show-toc", toc_file]
    #     show_result = subprocess.run(show_toc_cmd, capture_output=True, text=True)
    #     toc_output = show_result.stdout + show_result.stderr
    #     print("show-toc output:")
    #     print(toc_output)
    #     match = re.search(r"Leadout.*?\((\d+)\)", toc_output)
    #     if match:
    #         disc_sectors = int(match.group(1))

    try:
        disc_size = int(subprocess.check_output(["blockdev", "--getsize64", drive_path]).strip())
        print(f"Disc size via blockdev: {disc_size:,} bytes")
    except:
        disc_size = 700 * 1024 * 1024
        print(f"Using fallback size: {disc_size:,} bytes (700 MB)")

    disc_size_mb = disc_size // (1024 * 1024)

    # Find toc2cue
    toc2cue = shutil.which("toc2cue", path=ripdisc_path + ':' + os.environ.get('PATH', ''))
    if not toc2cue:
        msg = f"Error: toc2cue not found at {ripdisc_path}/toc2cue or in PATH"
        print(msg)
        cmd = [
            "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
            "--msgbox", msg, "12", "70"
        ]
        run_dialog(cmd)
        return

    # Start cdrdao read-cd, output to terminal as it happens
    cmd = [
        cdrdao, "read-cd", "--read-raw", "--datafile", bin_file, "--driver", "generic-mmc-raw",
        "--device", drive_path, "--read-subchan", "rw_raw", toc_file
    ]
    print(f"Starting cdrdao: {' '.join(cmd)}")
    cdrdao_proc = subprocess.Popen(cmd)

    # Gauge
    env = os.environ.copy()
    env["TERM"] = "linux"
    gauge_cmd = ["dialog", "--gauge", "RetroSpin", "12", "70", "0"]
    with open('/dev/tty', 'w') as tty, open(err_log, 'w') as err_f:
        gauge_proc = subprocess.Popen(gauge_cmd, stdin=subprocess.PIPE, stdout=tty, stderr=err_f, env=env, text=True)

    start_time = time.time()
    last_update = 0

    # Initial text with all fields, blanks for missing
    text = f"RetroSpin\nSaving {title}...\nSaved:  \nEstimated time remaining:  \nTransfer rate: "
    gauge_proc.stdin.write(f"XXX\n0\n{text}\nXXX\n")
    gauge_proc.stdin.flush()

    try:
        while cdrdao_proc.poll() is None:
            time.sleep(1)
            if not os.path.exists(bin_file):
                continue

            current_size = os.path.getsize(bin_file)
            current_mb = current_size // (1024 * 1024)
            percent = min(99, int((current_size / disc_size) * 100)) if disc_size > 0 else 0

            elapsed = time.time() - start_time
            rate = current_size / elapsed / (1024 * 1024) if elapsed > 0 else 0
            remaining_bytes = disc_size - current_size
            eta = remaining_bytes / (rate * 1024 * 1024) if rate > 0 else 0
            mins = int(eta // 60)
            secs = int(eta % 60)

            if time.time() - last_update >= 5:
                text = f"RetroSpin\nSaving {title}...\nSaved: {current_mb} MB / {disc_size_mb} MB\nEstimated time remaining: {mins} min {secs} sec\nTransfer rate: {rate:.2f} MB/s"
                gauge_proc.stdin.write(f"XXX\n{percent}\n{text}\nXXX\n")
                gauge_proc.stdin.flush()
                last_update = time.time()

        final_percent = 100 if cdrdao_proc.returncode == 0 else 0
        gauge_proc.stdin.write(f"XXX\n{final_percent}\nFinalizing...\nXXX\n")
        gauge_proc.stdin.flush()
        time.sleep(1)

    except Exception as e:
        print(f"Progress gauge error: {e}")
    finally:
        gauge_proc.stdin.close()
        gauge_proc.wait()
        if os.path.exists(err_log) and os.path.getsize(err_log) > 0:
            with open(err_log, "r") as f:
                print(f"Gauge dialog error: {f.read().strip()}")
            os.remove(err_log)

    cdrdao_status = cdrdao_proc.returncode
    cdrdao_proc = None

    if cdrdao_status == 0:
        print("Save to USB complete")

        if os.path.exists(toc_file):
            print(f"Converting .toc to .cue: {cue_file}")
            subprocess.run([toc2cue, toc_file, cue_file], check=True)
            if os.path.exists(cue_file):
                with open(cue_file, "r") as f:
                    content = f.read()
                content = content.replace(bin_file, f"{title}.bin")
                with open(cue_file, "w") as f:
                    f.write(content)
                print(f"Successfully created .cue file: {cue_file}")
            else:
                final_message = f"Error: Failed to create .cue file\n.bin file saved at {bin_file}"
                print(final_message)
                cmd = [
                    "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
                    "--msgbox", final_message, "12", "70"
                ]
                run_dialog(cmd)
                if os.path.exists(toc_file):
                    os.remove(toc_file)
                return
            os.remove(toc_file)
            print(f"Removed temporary .toc file: {toc_file}")
        else:
            final_message = f"Error: .toc file missing after cdrdao: {toc_file}\n.bin file saved at {bin_file}"
            print(final_message)
            cmd = [
                "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
                "--msgbox", final_message, "12", "70"
            ]
            run_dialog(cmd)
            return

        if os.path.exists(cue_file) and os.path.exists(bin_file):
            print(f"Successfully saved {cue_file} and {bin_file}")
            final_message = f"Disc saved successfully. Please close this dialog to restart the launcher and load {title}."
        else:
            print("Error: Missing .cue or .bin file after save")
            final_message = "Disc save incomplete. Check {cue_file} and {bin_file}."
    else:
        print("Error occurred during disc save. Check {bin_file} and {toc_file} for partial data.")
        final_message = f"Disc save failed. Partial data may be at {bin_file}. Close to restart launcher."

    print("Executing dialog: Final message")
    cmd = [
        "dialog", "--clear", "--backtitle", "RetroSpin", "--title", "RetroSpin",
        "--msgbox", f"RetroSpin\n{final_message}", "12", "50"
    ]
    run_dialog(cmd)

    print("Restarting RetroSpin launcher via retrospin_service.sh...")
    subprocess.run(["/media/fat/Scripts/retrospin_service.sh"])

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: save_disc.py <drive_path> <title> <system>")
        sys.exit(1)
    drive_path, title, system = sys.argv[1], sys.argv[2], sys.argv[3]
    save_disc(drive_path, title, system)