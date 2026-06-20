import sys, os, time, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from agents.research_agent import ResearchAgent
from agents.scriptwriting_agent import ScriptwritingAgent
from agents.voiceover_agent import VoiceoverAgent
from agents.broll_agent import BrollAgent
from agents.video_assembly_agent import VideoAssemblyAgent
from agents.thumbnail_agent import ThumbnailAgent
from agents.publishing_agent import PublishingAgent

TOPIC = "The Life of Harriet Tubman"
CATEGORY = "history"
SAFE_TOPIC = "".join(c if c.isalnum() or c in " -_" else "_" for c in TOPIC)[:40]

def main():
    os.makedirs("output", exist_ok=True)

    print("\n=== 1. RESEARCH ===")
    t0 = time.time()
    research_data = ResearchAgent().research(TOPIC)
    print(f"Research: {len(research_data)} results ({time.time()-t0:.1f}s)")

    print("\n=== 2. SCRIPTWRITING ===")
    t0 = time.time()
    sw = ScriptwritingAgent()
    script = sw.write_script(TOPIC, research_data, CATEGORY)
    print(f"Script: {len(script)} chars ({time.time()-t0:.1f}s)")

    print("\n=== 3. VOICEOVER ===")
    t0 = time.time()
    audio_path = VoiceoverAgent().generate_voiceover(script)
    print(f"Voiceover: {os.path.getsize(audio_path)/1024:.1f}KB ({time.time()-t0:.1f}s)")

    print("\n=== 4. B-ROLL ===")
    t0 = time.time()
    scene_markers = sw.parse_scene_markers(script)
    print(f"Found {len(scene_markers)} scene markers")
    broll_clips = []
    for i, marker in enumerate(scene_markers):
        try:
            clip = BrollAgent().get_clip(marker)
            broll_clips.append(clip)
            print(f"  [{i+1}/{len(scene_markers)}] OK")
        except Exception as e:
            print(f"  [{i+1}/{len(scene_markers)}] FAILED: {e}")
    print(f"B-roll: {len(broll_clips)} clips ({time.time()-t0:.1f}s)")

    if not broll_clips:
        print("ERROR: No broll clips. Aborting.")
        return

    print("\n=== 5. VIDEO ASSEMBLY ===")
    assembler = VideoAssemblyAgent()
    h_path = os.path.abspath(f"output/{SAFE_TOPIC}_horizontal.mp4")
    print("Assembling horizontal...")
    assembler.assemble(broll_clips, audio_path, h_path, vertical=False)
    print(f"Horizontal: {os.path.getsize(h_path)/1024:.1f}KB")

    print("Converting to vertical...")
    v_path = assembler.convert_to_vertical(h_path)
    print(f"Vertical: {os.path.getsize(v_path)/1024:.1f}KB")

    print("\n=== 6. THUMBNAIL ===")
    try:
        thumb_tmp = ThumbnailAgent().generate_thumbnail(TOPIC)
        import shutil
        thumb_path = os.path.abspath(f"output/{SAFE_TOPIC}_thumb.png")
        shutil.copy2(thumb_tmp, thumb_path)
        print(f"Thumbnail: {thumb_path}")
    except Exception as e:
        print(f"Thumbnail FAILED: {e}")
        thumb_path = None

    print("\n=== 7. YOUTUBE UPLOAD ===")
    title = f"{TOPIC} - Black History #shorts"
    desc = f"Discover the inspiring story of {TOPIC}. #blackhistory #education #shorts"
    url = PublishingAgent().publish_youtube_shorts(h_path, title, desc, thumb_path)
    print(f"YouTube: {url or 'skipped (no token)'}")

    print("\n=== FULL PIPELINE COMPLETE ===")

if __name__ == "__main__":
    main()
