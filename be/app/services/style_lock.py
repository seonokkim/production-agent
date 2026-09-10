"""Default generation look lock — photorealistic Korean drama / cinematic film still.

Applied when composing NEW generation prompts and shot-spec defaults.
Exact re-run keeps parent prompt / negative_prompt / workflow snapshot unchanged
(GenerationService.rerun overwrites the child row from the parent after submit).
"""

from __future__ import annotations

# Positive framing — live-action, not illustration.
STYLE_POSITIVE = (
    "photorealistic live-action Korean drama, cinematic film still, "
    "natural skin texture, grounded production lighting, shallow depth of field, "
    "35mm anamorphic look, 16:9"
)

# Hard bans — never anime / manga / cartoon / cute / RPG / illustration.
STYLE_NEGATIVE = (
    "anime, manga, cartoon, comic, cel shading, chibi, cute stylized, "
    "illustration, digital art, painting, drawing, sketch, concept art, "
    "RPG, fantasy game art, 3d render look, unreal engine, "
    "blurry, low quality, watermark, text overlay, deformed, "
    "extra fingers, plastic skin, oversaturated neon cartoon"
)

_STYLE_MARKERS = (
    "photorealistic live-action",
    "korean drama",
    "cinematic film still",
)


def default_negative_prompt() -> str:
    return STYLE_NEGATIVE


def _already_styled(text: str) -> bool:
    lower = (text or "").lower()
    return any(m in lower for m in _STYLE_MARKERS)


def compose_keyframe_prompt(visual_prompt: str) -> str:
    """Final positive prompt for keyframe / SDXL."""
    body = (visual_prompt or "").strip()
    if not body:
        body = "dramatic scene"
    if _already_styled(body):
        return body
    return f"{STYLE_POSITIVE}, {body}"


def compose_motion_prompt(motion_prompt: str) -> str:
    """Final positive prompt for I2V / Wan."""
    body = (motion_prompt or "").strip()
    if not body:
        body = "subtle cinematic camera move, natural motion"
    if _already_styled(body):
        return body
    return (
        f"{STYLE_POSITIVE}, live-action continuous shot, natural motion, "
        f"no stylization, {body}"
    )


def shot_spec_visual_template(
    *,
    location: str,
    time_of_day: str,
    subjects: str,
    action: str,
    shot_size: str,
    camera_angle: str,
    lighting: str,
    mood: str,
) -> str:
    return (
        f"{STYLE_POSITIVE}, {location}, {time_of_day}, {subjects}, {action}, "
        f"{shot_size}, {camera_angle}, {lighting}, {mood}"
    )


def shot_spec_motion_template(*, camera_motion: str, action: str, mood: str) -> str:
    return (
        f"{STYLE_POSITIVE}, live-action continuous shot, {camera_motion}, "
        f"{action}, {mood}, natural motion, no stylization"
    )


LLM_STYLE_SYSTEM_EXTRA = (
    "Style lock (mandatory): visual_prompt and motion_prompt must describe "
    "photorealistic live-action Korean drama / cinematic film still photography. "
    "Never use anime, manga, cartoon, cute, chibi, RPG, illustration, painting, "
    "or stylized digital art language. Prefer natural skin, grounded lighting, "
    "and film-still wording."
)
