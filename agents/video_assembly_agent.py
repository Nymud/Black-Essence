import logging
import os
import subprocess
import tempfile
import shutil
import re

from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import numpy as np

import whisper

from utils.config import Config

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
HANDWRITING_FONT = "Patrick Hand"


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
    def _ass_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    def _convert_to_sketch(self, image_path: str) -> str:
        img = Image.open(image_path).convert("RGB").resize((1280, 720), Image.LANCZOS)
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edges, dtype=np.float32)
        emax, emin = float(edge_arr.max()), float(edge_arr.min())
        span = emax - emin
        if span > 0:
            edge_norm = ((edge_arr - emin) / span * 255).astype(np.uint8)
        else:
            edge_norm = np.zeros_like(edge_arr, dtype=np.uint8)
        threshold = 30
        strong = Image.fromarray((edge_norm > threshold).astype(np.uint8) * 255, "L")
        dilated = strong.filter(ImageFilter.MaxFilter(3))
        dilated = dilated.filter(ImageFilter.MaxFilter(3))
        dilated = dilated.filter(ImageFilter.MaxFilter(3))
        sketch = Image.new("L", dilated.size, 255)
        sketch.paste(dilated)
        rgb = Image.new("RGB", sketch.size, (252, 252, 245))
        rgb.paste(sketch)
        out = tempfile.NamedTemporaryFile(suffix=".png", prefix="sketch_", delete=False)
        out_path = out.name
        out.close()
        rgb.save(out_path, "PNG")
        return out_path

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
    def _write_ass(srt_path: str, ass_path: str, target_w: int, target_h: int):
        with open(srt_path, "r", encoding="utf-8") as f:
            srt_content = f.read()

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {target_w}
PlayResY: {target_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{HANDWRITING_FONT},28,&H00000000,&H000000FF,&HFFFFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = []
        for block in re.split(r"\n\n+", srt_content.strip()):
            block = block.strip()
            if not block:
                continue
            parts = block.split("\n", 2)
            if len(parts) < 3:
                continue
            _, time_line, text = parts
            text = text.replace("\n", "\\N")
            match = re.match(r"(\d+:\d+:\d+[.,]\d+) --> (\d+:\d+:\d+[.,]\d+)", time_line)
            if match:
                start = match.group(1).replace(",", ".")
                end = match.group(2).replace(",", ".")
                lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            for line in lines:
                f.write(line + "\n")

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
        import tempfile, shutil
        from PIL import Image as PILImage
        import numpy as np

        reveal_sec = min(2.0, duration * 0.3)
        total_frames = max(1, int(duration * fps))
        reveal_frames = max(1, int(reveal_sec * fps))

        scale = 1.08
        sw, sh = int(w * scale), int(h * scale)
        try:
            src = PILImage.open(image_path).convert("RGB").resize((sw, sh), PILImage.LANCZOS)
        except Exception:
            src = PILImage.new("RGB", (sw, sh), "white")
        img_arr = np.array(src)

        frame_dir = tempfile.mkdtemp(prefix="anim_frames_")
        try:
            for i in range(total_frames):
                if i < reveal_frames:
                    t = i / max(reveal_frames - 1, 1)
                    t = t * t * (3 - 2 * t)
                    reveal_x = int(sw * t)
                    frame = np.full_like(img_arr, 255)
                    if reveal_x > 0:
                        frame[:, :reveal_x] = img_arr[:, :reveal_x]
                    frame = PILImage.fromarray(frame).resize((w, h), PILImage.LANCZOS)
                else:
                    t_hold = (i - reveal_frames) / max(fps, 1)
                    zoom = 1.0 + 0.003 * t_hold
                    crop_w = max(1, int(sw / zoom))
                    crop_h = max(1, int(sh / zoom))
                    cx = (sw - crop_w) // 2
                    cy = (sh - crop_h) // 2
                    cropped = PILImage.fromarray(img_arr).crop((cx, cy, cx + crop_w, cy + crop_h))
                    frame = cropped.resize((w, h), PILImage.LANCZOS)
                frame.save(os.path.join(frame_dir, f"frame_{i:04d}.png"))

            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", os.path.join(frame_dir, "frame_%04d.png"),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-an",
                "-t", str(duration),
                out_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        finally:
            shutil.rmtree(frame_dir, ignore_errors=True)

    def _create_video_segment(self, video_path: str, duration: float, w: int, h: int, fps: int, out_path: str):
        if not os.path.isfile(video_path) or os.path.getsize(video_path) == 0:
            logger.warning("Video %s missing/empty, generating blank segment", video_path)
            self._gen_blank(duration, w, h, fps, out_path)
            return
        vf = f"scale={w}:{h}:force_original_aspect_ratio=1,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=white"
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
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        except subprocess.CalledProcessError:
            logger.warning("First attempt failed for %s, trying with stream copy", video_path)
            cmd2 = [
                "ffmpeg", "-y", "-i", video_path,
                "-c", "copy", "-an",
                "-t", str(duration),
                "-fflags", "+genpts",
                "-avoid_negative_ts", "make_zero",
                os.path.join(os.path.dirname(out_path), "_reencoded.mp4")
            ]
            try:
                subprocess.run(cmd2, check=True, capture_output=True, text=True, timeout=120)
                reencoded = cmd2[-1]
                cmd3 = [
                    "ffmpeg", "-y", "-i", reencoded,
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-an",
                    "-r", str(fps),
                    "-t", str(duration),
                    out_path
                ]
                subprocess.run(cmd3, check=True, capture_output=True, text=True, timeout=300)
            except Exception:
                logger.warning("Video segment re-encode failed, generating blank segment")
                self._gen_blank(duration, w, h, fps, out_path)

    @staticmethod
    def _gen_blank(duration: float, w: int, h: int, fps: int, out_path: str):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=white@0.95:s={w}x{h}:d={duration}:r={fps}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-pix_fmt", "yuv420p",
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)

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
            ass_path = os.path.join(tmp, "subs.ass")
            srt_path = os.path.join(tmp, "subs.srt")
            self._write_srt(segments, srt_path)
            self._write_ass(srt_path, ass_path, target_w, target_h)

            seg_paths = []
            for i, clip_path in enumerate(broll_clips):
                out_seg = os.path.join(tmp, f"s{i:04d}.mp4")
                if self._is_image(clip_path):
                    self._create_image_segment(clip_path, clip_duration, target_w, target_h, fps, out_seg)
                else:
                    self._create_video_segment(clip_path, clip_duration, target_w, target_h, fps, out_seg)
                seg_paths.append(out_seg)

            concat_file = os.path.join(tmp, "concat.txt")
            with open(concat_file, "w") as f:
                for sp in seg_paths:
                    f.write(f"file '{sp.replace(os.sep, '/')}'\n")

            joined = os.path.join(tmp, "joined.mp4")
            cmd_join = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                joined
            ]
            subprocess.run(cmd_join, check=True, capture_output=True, text=True, timeout=120)

            with_subs = os.path.join(tmp, "with_subs.mp4")
            fonts_tmp = os.path.join(tmp, "fonts")
            os.makedirs(fonts_tmp, exist_ok=True)
            for f in os.listdir(FONTS_DIR):
                shutil.copy2(os.path.join(FONTS_DIR, f), fonts_tmp)
            cmd_subs = [
                "ffmpeg", "-y", "-i", joined,
                "-vf", f"ass={os.path.basename(ass_path)}:fontsdir=fonts",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-pix_fmt", "yuv420p",
                with_subs
            ]
            subprocess.run(cmd_subs, cwd=tmp, check=True, capture_output=True, text=True, timeout=300)

            cmd_audio = [
                "ffmpeg", "-y", "-i", with_subs, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", "-movflags", "+faststart",
                output_path
            ]
            subprocess.run(cmd_audio, check=True, capture_output=True, text=True, timeout=300)

            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  Output: {output_path} [{size_mb:.1f} MB]")
            logger.info("Video assembled to %s", output_path)
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timed out for %s", output_path)
            raise RuntimeError(f"ffmpeg timed out for {output_path}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            stdout = e.stdout or ""
            logger.error("ffmpeg failed for %s with exit code %s", output_path, e.returncode)
            logger.error("ffmpeg stderr: %s", stderr[-1000:] if stderr else "(empty)")
            logger.error("ffmpeg stdout: %s", stdout[-500:] if stdout else "(empty)")
            raise RuntimeError(f"ffmpeg failed (exit {e.returncode}): {stderr[-2000:] if stderr else 'no stderr'}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def convert_to_vertical(self, input_path: str) -> str:
        out = tempfile.NamedTemporaryFile(suffix="_vertical.mp4", delete=False)
        out_path = out.name
        out.close()

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=720:1280:force_original_aspect_ratio=1,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=white",
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
