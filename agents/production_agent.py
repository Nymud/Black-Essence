import logging
import os
import tempfile
from datetime import datetime

from agents.voiceover_agent import VoiceoverAgent
from agents.broll_agent import BrollAgent
from agents.video_assembly_agent import VideoAssemblyAgent
from agents.thumbnail_agent import ThumbnailAgent
from agents.scriptwriting_agent import ScriptwritingAgent
from utils.config import Config
from utils.fallbacks import critical_failure_alert

logger = logging.getLogger(__name__)


class ProductionResult:
    def __init__(self, script: str, video_path: str, vertical_path: str, thumbnail_path: str, topic: str):
        self.script = script
        self.video_path = video_path
        self.vertical_path = vertical_path
        self.thumbnail_path = thumbnail_path
        self.topic = topic


class ProductionAgent:
    def __init__(self, telegram_bot=None):
        self.voiceover = VoiceoverAgent()
        self.broll = BrollAgent()
        self.video_assembly = VideoAssemblyAgent()
        self.thumbnail = ThumbnailAgent()
        self.scriptwriter = ScriptwritingAgent()
        self.telegram_bot = telegram_bot
        self.output_dir = Config.OUTPUT_DIR

    def produce(self, topic: str, category: str = "general") -> ProductionResult:
        os.makedirs(self.output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic)[:40]

        try:
            logger.info("Starting scriptwriting for: %s", topic)
            research_data = []
            script = self.scriptwriter.write_script(topic, research_data, category)
            # If research agent was available, re-run with it
            try:
                from agents.research_agent import ResearchAgent
                researcher = ResearchAgent()
                research_data = researcher.research(topic)
                script = self.scriptwriter.write_script(topic, research_data, category)
            except Exception as e:
                logger.warning("Research agent failed, using LLM-only script: %s", e)

            logger.info("Script written (%d chars)", len(script))

            scene_markers = self.scriptwriter.parse_scene_markers(script)
            if not scene_markers:
                logger.warning("No SCENE markers found, using topic-based markers")
                scene_markers = [topic]

            logger.info("Generating voiceover...")
            audio_path = self.voiceover.generate_voiceover(script)

            logger.info("Fetching %d scene images...", len(scene_markers))
            broll_clips = []
            for marker in scene_markers:
                try:
                    clip = self.broll.get_clip(marker)
                    broll_clips.append(clip)
                except Exception as e:
                    logger.error("Failed to fetch broll for '%s': %s", marker, e)

            if not broll_clips:
                logger.warning("No b-roll clips fetched, using black placeholders")
                blank = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                blank.close()
                broll_clips.append(blank.name)

            video_name = f"{safe_topic}_{ts}.mp4"
            video_path = os.path.join(self.output_dir, video_name)
            logger.info("Assembling video...")
            self.video_assembly.assemble(broll_clips, audio_path, video_path, vertical=False)

            vertical_name = f"{safe_topic}_{ts}_vertical.mp4"
            vertical_path = os.path.join(self.output_dir, vertical_name)
            logger.info("Converting to vertical format...")
            vertical_path = self.video_assembly.convert_to_vertical(video_path)

            logger.info("Generating thumbnail...")
            thumb_path = self.thumbnail.generate_thumbnail(topic)

            logger.info("Production complete for: %s", topic)
            return ProductionResult(script, video_path, vertical_path, thumb_path, topic)

        except Exception as e:
            error_msg = critical_failure_alert("ProductionAgent", e)
            raise RuntimeError(error_msg) from e
