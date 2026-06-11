import sys, logging, os, tempfile
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

topic = "The Life of Harriet Tubman"

# Step 1: Research
from agents.research_agent import ResearchAgent
results = ResearchAgent().research(topic)
print(f"[OK] Research: {len(results)} results")

# Step 2: Script
from agents.scriptwriting_agent import ScriptwritingAgent
script = ScriptwritingAgent().write_script(topic, results)
print(f"[OK] Script: {len(script)} chars")

# Step 3: Voiceover
from agents.voiceover_agent import VoiceoverAgent
audio_path = VoiceoverAgent().generate_voiceover(script)
print(f"[OK] Voiceover: {audio_path}")

# Step 4: B-ROLL clips
from agents.broll_agent import BrollAgent
b = BrollAgent()
keywords = ["Harriet Tubman", "underground railroad", "slavery", "freedom", "history"]
broll_paths = []
for kw in keywords[:3]:
    try:
        p = b.get_clip(kw)
        broll_paths.append(p)
        print(f"[OK] B-ROLL clip: {p}")
    except Exception as e:
        print(f"[SKIP] B-ROLL '{kw}': {e}")

# Step 5: Video Assembly
from agents.video_assembly_agent import VideoAssemblyAgent
os.makedirs("output", exist_ok=True)
va = VideoAssemblyAgent()
horizontal_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_horizontal.mp4")
vertical_path = os.path.abspath(f"output/{topic.replace(' ', '_')}_vertical.mp4")

print("Assembling horizontal (16:9)...")
va.assemble(broll_clips=broll_paths, audio_path=audio_path, output_path=horizontal_path, vertical=False)
print("[OK] Horizontal video done")

print("Assembling vertical (9:16)...")
va.assemble(broll_clips=broll_paths, audio_path=audio_path, output_path=vertical_path, vertical=True)
print("[OK] Vertical video done")
