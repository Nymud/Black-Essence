import logging
import os
import tempfile
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, ColorClip
from moviepy.video.tools.subtitles import SubtitlesClip
import whisper
import numpy as np

from utils.config import Config

logger = logging.getLogger(__name__)


class VideoAssemblyAgent:
    def __init__(self):
        self.whisper_model_name = Config.WHISPER_MODEL
        self._whisper_model = None

    def _get_whisper(self):
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(self.whisper_model_name)
        return self._whisper_model

    def _transcribe_audio(self, audio_path: str) -> list[dict]:
        model = self._get_whisper()
        result = model.transcribe(audio_path)
        return result.get("segments", [])

    def _create_subtitle_clips(self, segments, video_width, video_height):
        clips = []
        font_size = max(24, int(video_height * 0.04))
        margin_bottom = int(video_height * 0.08)

        for seg in segments:
            txt = seg.get("text", "").strip()
            if not txt:
                continue
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            duration = end - start

            txt_clip = TextClip(
                txt,
                fontsize=font_size,
                color="white",
                font="Arial",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(int(video_width * 0.9), None),
            )
            txt_clip = txt_clip.set_start(start).set_duration(duration)
            txt_clip = txt_clip.set_position(("center", video_height - margin_bottom - txt_clip.h))
            clips.append(txt_clip)

        return clips

    def assemble(self, broll_clips: list[str], audio_path: str, output_path: str, vertical: bool = False):
        logger.info("Assembling video: %d clips, audio: %s", len(broll_clips), audio_path)

        target_w, target_h = (1080, 1920) if vertical else (1920, 1080)

        video_clips = []
        current_time = 0

        audio = AudioFileClip(audio_path)
        total_duration = audio.duration

        clip_duration = total_duration / max(len(broll_clips), 1)

        for i, clip_path in enumerate(broll_clips):
            try:
                clip = VideoFileClip(clip_path)
                if vertical:
                    clip = clip.resize(height=target_h)
                    clip = clip.crop(x_center=clip.w / 2, width=target_w)
                else:
                    clip = clip.resize(width=target_w)
                    clip = clip.crop(y_center=clip.h / 2, height=target_h)

                clip = clip.set_duration(min(clip_duration, clip.duration))
                clip = clip.set_start(current_time)
                video_clips.append(clip)
                current_time += clip.duration
            except Exception as e:
                logger.warning("Failed to process clip %s: %s", clip_path, e)
                blank = ColorClip(size=(target_w, target_h), color=(0, 0, 0))
                blank = blank.set_duration(clip_duration).set_start(current_time)
                video_clips.append(blank)
                current_time += clip_duration

        final = CompositeVideoClip(video_clips, size=(target_w, target_h))
        final = final.set_audio(audio)
        final = final.set_duration(total_duration)

        segments = self._transcribe_audio(audio_path)
        subtitle_clips = self._create_subtitle_clips(segments, target_w, target_h)
        if subtitle_clips:
            final = CompositeVideoClip([final] + subtitle_clips, size=(target_w, target_h))

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="fast",
            bitrate="3000k",
            threads=2,
        )

        for c in video_clips:
            try:
                c.close()
            except Exception:
                pass
        audio.close()
        final.close()

        logger.info("Video assembled to %s", output_path)
        return output_path

    def convert_to_vertical(self, input_path: str) -> str:
        out = tempfile.NamedTemporaryFile(suffix="_vertical.mp4", delete=False)
        out_path = out.name
        out.close()

        clip = VideoFileClip(input_path)
        w, h = clip.size
        target_w, target_h = 1080, 1920

        if w / h > target_w / target_h:
            new_w = int(h * target_w / target_h)
            clip_resized = clip.resize(width=new_w)
            clip_cropped = clip_resized.crop(x_center=clip_resized.w / 2, width=target_w)
        else:
            new_h = int(w * target_h / target_w)
            clip_resized = clip.resize(height=new_h)
            clip_cropped = clip_resized.crop(y_center=clip_resized.h / 2, height=target_h)

        clip_cropped = clip_cropped.resize((target_w, target_h))
        clip_cropped.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="fast",
        )
        clip.close()
        clip_cropped.close()
        logger.info("Converted to vertical: %s", out_path)
        return out_path
