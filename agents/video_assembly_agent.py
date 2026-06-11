import logging
import os
import subprocess
import tempfile
import shutil
import re

import whisper

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

    @staticmethod
    def _srt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    @staticmethod
    def _write_srt(segments: list[dict], path: str):
        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, 1):
                text = seg.get("text", "").strip()
                if not text:
                    continue
                start = seg.get("start", 0)
                end = seg.get("end", 0)
                if end - start < 0.3:
                    continue
                f.write(f"{i}\n")
                f.write(f"{VideoAssemblyAgent._srt_time(start)} --> {VideoAssemblyAgent._srt_time(end)}\n")
                f.write(f"{text}\n\n")

    @staticmethod
    def _get_duration(path: str) -> float:
        cmd = ["ffmpeg", "-i", path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            h, mn, s = m.groups()
            return int(h) * 3600 + int(mn) * 60 + float(s)
        raise RuntimeError(f"Could not parse duration from {path}")

    @staticmethod
    def _is_image(path: str) -> bool:
        return path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))

    def _create_image_segment(self, image_path: str, duration: float, w: int, h: int, fps: int, out_path: str):
        n_frames = max(1, int(duration * fps))
        inc = 0.06 / n_frames
        scale_w = int(w * 1.06)
        scale_h = int(h * 1.06)
        vf = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z=if(eq(on\\,1)\\,1\\,zoom+{inc}):d={n_frames}:s={w}x{h}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            "-an",
            "-t", str(duration),
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)

    def _create_video_segment(self, video_path: str, duration: float, w: int, h: int, fps: int, out_path: str):
        vf = f"scale={w}:{h}:force_original_aspect_ratio=1,crop={w}:{h}"
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            "-an",
            "-t", str(duration),
            "-r", str(fps),
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)

    def assemble(self, broll_clips: list[str], audio_path: str, output_path: str, vertical: bool = False):
        logger.info("Assembling video: %d clips, audio: %s", len(broll_clips), audio_path)
        target_w, target_h = (720, 1280) if vertical else (1280, 720)
        fps = 12

        audio_duration = self._get_duration(audio_path)
        clip_duration = audio_duration / max(len(broll_clips), 1)
        print(f"\n=== VIDEO: {audio_duration:.0f}s @ {target_w}x{target_h}, {fps}fps ===")
        print(f"  {len(broll_clips)} segments, {clip_duration:.1f}s each")

        tmp = tempfile.mkdtemp(prefix="vid_")
        try:
            segments = self._transcribe_audio(audio_path)
            srt_path = os.path.join(tmp, "subs.srt")
            self._write_srt(segments, srt_path)

            seg_paths = []
            for i, clip_path in enumerate(broll_clips):
                out_seg = os.path.join(tmp, f"s{i:04d}.mp4")
                if self._is_image(clip_path):
                    self._create_image_segment(clip_path, clip_duration, target_w, target_h, fps, out_seg)
                else:
                    self._create_video_segment(clip_path, clip_duration, target_w, target_h, fps, out_seg)
                seg_paths.append(out_seg)

            concat_path = os.path.join(tmp, "concat.txt")
            with open(concat_path, "w") as f:
                for sp in seg_paths:
                    f.write(f"file '{os.path.basename(sp)}'\n")

            subtitles_filter = (
                "subtitles=subs.srt"
                ":force_style='Alignment=2,FontName=Arial,FontSize=16,"
                "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'"
            )

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-vf", subtitles_filter,
                "-shortest",
                "-movflags", "+faststart",
                output_path
            ]

            subprocess.run(cmd, cwd=tmp, check=True, capture_output=True, text=True, timeout=1800)
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  Output: {output_path} [{size_mb:.1f} MB]")
            logger.info("Video assembled to %s", output_path)
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timed out for %s", output_path)
            raise RuntimeError(f"ffmpeg timed out for {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error("ffmpeg failed: %s", e.stderr[:500])
            raise RuntimeError(f"ffmpeg failed: {e.stderr[:200]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def convert_to_vertical(self, input_path: str) -> str:
        out = tempfile.NamedTemporaryFile(suffix="_vertical.mp4", delete=False)
        out_path = out.name
        out.close()

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=720:1280:force_original_aspect_ratio=1,crop=720:1280",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        logger.info("Converted to vertical: %s", out_path)
        return out_path
