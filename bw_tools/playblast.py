import bpy
import os
import subprocess
import sys


def _open_in_default_player(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def run_playblast(play_when_done=False):
    """Render an OpenGL viewport playblast to an .mp4 next to the .blend file.

    With play_when_done, open the finished movie in the system's default player.
    """
    scene = bpy.context.scene

    # ── 1. Resolve paths ──────────────────────────────────────────
    blend_filepath = bpy.data.filepath
    if blend_filepath:
        blend_filename = bpy.path.basename(blend_filepath)
        blend_name = os.path.splitext(blend_filename)[0]
    else:
        blend_name = "untitled"

    playblast_path = f"//../Playblast/{blend_name}.mp4"

    # ── 2. Save current output settings ───────────────────────────
    orig_filepath = scene.render.filepath
    orig_format = scene.render.image_settings.file_format

    has_media_type = hasattr(scene.render.image_settings, 'media_type')
    if has_media_type:
        orig_media_type = scene.render.image_settings.media_type

    try:
        orig_ffmpeg_format = scene.render.ffmpeg.format
        orig_ffmpeg_codec = scene.render.ffmpeg.codec
        orig_crf = scene.render.ffmpeg.constant_rate_factor
        orig_audio_codec = scene.render.ffmpeg.audio_codec
        orig_audio_bitrate = scene.render.ffmpeg.audio_bitrate
        orig_audio_channels = scene.render.ffmpeg.audio_channels
    except Exception:
        orig_ffmpeg_format = 'MPEG4'
        orig_ffmpeg_codec = 'H264'
        orig_crf = 'MEDIUM'
        orig_audio_codec = 'NONE'
        orig_audio_bitrate = 192
        orig_audio_channels = 'STEREO'

    # ── 3. Set output to MP4 ──────────────────────────────────────
    scene.render.filepath = playblast_path

    if has_media_type:
        scene.render.image_settings.media_type = 'VIDEO'

    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.audio_codec = 'AAC'
    scene.render.ffmpeg.audio_bitrate = 192
    scene.render.ffmpeg.audio_channels = 'STEREO'

    try:
        # ── 4. Render directly from the active viewport ───────────
        print(f"[Playblast] Starting -> {playblast_path}")

        bpy.ops.render.opengl(animation=True)

        print("[Playblast] Completed successfully.")

        # The animation operator blocks until ffmpeg has closed the file, so it is safe to open.
        if play_when_done:
            movie_path = os.path.normpath(bpy.path.abspath(playblast_path))
            if os.path.isfile(movie_path):
                _open_in_default_player(movie_path)
            else:
                print(f"[Playblast] Movie not found, not playing: {movie_path}")

    except Exception as e:
        print(f"[Playblast] Error: {e}")

    finally:
        # ── 5. Restore original settings ──────────────────────────
        if has_media_type:
            scene.render.image_settings.media_type = orig_media_type

        scene.render.image_settings.file_format = orig_format
        scene.render.filepath = orig_filepath

        try:
            scene.render.ffmpeg.format = orig_ffmpeg_format
            scene.render.ffmpeg.codec = orig_ffmpeg_codec
            scene.render.ffmpeg.constant_rate_factor = orig_crf
            scene.render.ffmpeg.audio_codec = orig_audio_codec
            scene.render.ffmpeg.audio_bitrate = orig_audio_bitrate
            scene.render.ffmpeg.audio_channels = orig_audio_channels
        except Exception:
            pass

        print("[Playblast] Settings restored.")
