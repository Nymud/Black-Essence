import sys, logging, os, time
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

topic = "The Life of Harriet Tubman"

times = {}

# Step 1: Research
from agents.research_agent import ResearchAgent
t0 = time.time()
results = ResearchAgent().research(topic)
times["research"] = time.time() - t0
print(f"[OK] Research: {len(results)} results ({times['research']:.1f}s)")

# Step 2: Script
from agents.scriptwriting_agent import ScriptwritingAgent
t0 = time.time()
sw = ScriptwritingAgent()
script = sw.write_script(topic, results)
times["script"] = time.time() - t0
print(f"[OK] Script: {len(script)} chars ({times['script']:.1f}s)")
print(f"--- SCRIPT ---\n{script}\n--- END ---")

# Parse scene markers
scene_markers = sw.parse_scene_markers(script)
print(f"[INFO] Found {len(scene_markers)} scene markers")

# Step 3: Voiceover
from agents.voiceover_agent import VoiceoverAgent
t0 = time.time()
audio_path = VoiceoverAgent().generate_voiceover(script)
times["voiceover"] = time.time() - t0
print(f"[OK] Voiceover: {audio_path} ({times['voiceover']:.1f}s)")

# Step 4: Generate scene images
from agents.broll_agent import BrollAgent
b = BrollAgent()
broll_paths = []
times["broll"] = 0
if scene_markers:
    markers = scene_markers
else:
    markers = ["Harriet Tubman", "underground railroad", "freedom"]
print(f"Generating {len(markers)} scene images...")
for marker in markers:
    try:
        t0 = time.time()
        p = b.get_clip(marker)
        dur = time.time() - t0
        times["broll"] += dur
        broll_paths.append(p)
        print(f"[OK] Scene image: {os.path.basename(p)} ({dur:.1f}s)")
    except Exception as e:
        print(f"[SKIP] Scene '{marker}': {e}")

# Step 5: Video Assembly
from agents.video_assembly_agent import VideoAssemblyAgent
os.makedirs("output", exist_ok=True)
va = VideoAssemblyAgent()
horizontal_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_horizontal.mp4")
vertical_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_vertical.mp4")

print("Assembling horizontal (16:9)...")
t0 = time.time()
va.assemble(broll_clips=broll_paths, audio_path=audio_path, output_path=horizontal_path, vertical=False)
times["horizontal"] = time.time() - t0
print(f"[OK] Horizontal video done ({times['horizontal']:.0f}s)")

print("Assembling vertical (9:16)...")
t0 = time.time()
va.assemble(broll_clips=broll_paths, audio_path=audio_path, output_path=vertical_path, vertical=True)
times["vertical"] = time.time() - t0
print(f"[OK] Vertical video done ({times['vertical']:.0f}s)")

print("\n=== SUMMARY ===")
for k, v in times.items():
    print(f"  {k}: {v:.1f}s")
print(f"  TOTAL: {sum(times.values()):.0f}s")
print(f"  Files: {horizontal_path} ({os.path.getsize(horizontal_path)//1024}KB)")
print(f"         {vertical_path} ({os.path.getsize(vertical_path)//1024}KB)")
