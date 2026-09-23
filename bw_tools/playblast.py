import bpy
import os


def run_playblast():
    """Render an OpenGL viewport playblast to an .mp4 next to the .blend file."""
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
    except Exception:
        orig_ffmpeg_format = 'MPEG4'
        orig_ffmpeg_codec = 'H264'
        orig_crf = 'MEDIUM'

    # ── 3. Set output to MP4 ──────────────────────────────────────
    scene.render.filepath = playblast_path

    if has_media_type:
        scene.render.image_settings.media_type = 'VIDEO'

    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'

    try:
        # ── 4. Render directly from the active viewport ───────────
        print(f"[Playblast] Starting -> {playblast_path}")

        bpy.ops.render.opengl(animation=True)

        print("[Playblast] Completed successfully.")

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
        except Exception:
            pass

        print("[Playblast] Settings restored.")
