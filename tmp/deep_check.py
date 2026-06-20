import subprocess, os, sys, json

video = r"output\The Life of Harriet Tubman_horizontal.mp4"
if not os.path.exists(video):
    print("Video not found")
    sys.exit(1)

# Get FULL ffmpeg info
result = subprocess.run(
    ['ffmpeg', '-i', video],
    capture_output=True, text=True, timeout=30
)
print("=== STDERR ===")
print(result.stderr)
print("=== STDOUT ===")
print(result.stdout)
print(f"=== EXIT CODE: {result.returncode} ===")
print(f"=== FILE SIZE: {os.path.getsize(video)} ===")
