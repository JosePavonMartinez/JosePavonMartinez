"""Render a self-contained GitHub README GIF from the local PokéAPI sprites.

Run: python -m pip install -r requirements.txt
     python scripts/generate_pokemon_parade.py

No network, system fonts, random values, or intermediate frame files are used.
"""

from bisect import bisect_right
from dataclasses import dataclass
from math import pi, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/pokemon-parade.gif"
WIDTH, HEIGHT = 900, 190
FPS, LOOP_MS = 16, 16_000
BACKGROUND = "#11121c"
BORDER = "#414868"
MUTED = "#565f89"
PURPLE = "#bb9af7"
YELLOW = "#e0af68"
RED = "#f7768e"
FONT = ImageFont.load_default_imagefont()  # Bundled bitmap monospace font.


@dataclass(frozen=True)
class Actor:
    name: str
    size: int  # Longest visible dimension, not a padded source canvas.
    enter: float
    exit: float
    feet: int = 147
    phase: float = 0


# Followers keep roughly a sprite's width between them; Dragonite trails above.
ACTORS = (
    Actor("gengar", 90, 2.8, 8.2),
    Actor("pikachu", 70, 3.3, 9.65, 147, 0.4),
    Actor("charmander", 70, 4.0, 10.3, 145, 1.1),
    Actor("squirtle", 64, 4.7, 10.95, 148, 2.0),
    Actor("bulbasaur", 66, 5.4, 11.75, 146, 2.7),
    Actor("dragonite", 94, 6.0, 12.2, phase=0.6),
)


@dataclass
class Sprite:
    frames: list[Image.Image]
    ends: list[int]

    @property
    def size(self) -> tuple[int, int]:
        return self.frames[0].size

    def frame_at(self, elapsed: float) -> Image.Image:
        # Sample original GIF frame durations instead of advancing once per tick.
        millis = round(elapsed * 1000) % self.ends[-1]
        return self.frames[bisect_right(self.ends, millis)]


def load_sprite(actor: Actor) -> Sprite:
    path = ROOT / "assets/pokemon" / f"{actor.name}.gif"
    if not path.is_file():
        raise FileNotFoundError(f"Missing local sprite: {path}")
    frames, ends = [], []
    with Image.open(path) as source:
        for frame in ImageSequence.Iterator(source):
            # Pillow composites source GIF disposal/transparency before conversion.
            frames.append(frame.convert("RGBA"))
            ends.append((ends[-1] if ends else 0) + max(10, frame.info.get("duration", 100)))
    bounds = [frame.getbbox() for frame in frames if frame.getbbox()]
    if not bounds:
        raise ValueError(f"Sprite is entirely transparent: {path}")
    # One union crop preserves native animation alignment across all source frames.
    box = (min(b[0] for b in bounds), min(b[1] for b in bounds),
           max(b[2] for b in bounds), max(b[3] for b in bounds))
    scale = actor.size / max(box[2] - box[0], box[3] - box[1])
    size = (round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale))
    return Sprite([frame.crop(box).resize(size, Image.Resampling.NEAREST)
                   for frame in frames], ends)


def right_text(draw: ImageDraw.ImageDraw, y: int, text: str, color: str) -> int:
    x = WIDTH - 32 - round(draw.textlength(text, font=FONT))
    draw.text((x, y), text, font=FONT, fill=color)
    return x


def make_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((10, 10, 889, 179), radius=12, outline=BORDER)
    draw.text((32, 20), "WILD_PROCESS.exe", font=FONT, fill=MUTED)
    draw.line((24, 37, 875, 37), fill="#202233")
    # A restrained 32-step neon line, with a dark two-pixel halo underneath.
    draw.line((32, 151, 867, 151), fill="#252239", width=3)
    stops = ((122, 162, 247), (187, 154, 247), (255, 121, 198))
    for step in range(32):
        pos = step / 31 * 2
        segment = min(1, int(pos))
        amount = pos - segment
        color = tuple(round(a + (b - a) * amount)
                      for a, b in zip(stops[segment], stops[segment + 1]))
        left, right = 32 + step * 836 // 32, 32 + (step + 1) * 836 // 32 - 1
        draw.line((left, 151, right, 151), fill=color)
    draw.text((32, 163), "PID 0094", font=FONT, fill=MUTED)
    right_text(draw, 163, "STATUS: definitely intentional", MUTED)
    return image


def make_palette(background: Image.Image, sprites: dict[str, Sprite]) -> Image.Image:
    # Exact shared colors avoid dithering, palette flicker, and sprite color loss.
    colors = set(background.get_flattened_data())
    for color in (PURPLE, YELLOW, RED, "#30263b", "#282432", "#1c1e2d"):
        colors.add(tuple(bytes.fromhex(color[1:])))
    for sprite in sprites.values():
        for frame in sprite.frames:
            colors.update(pixel[:3] for pixel in frame.get_flattened_data() if pixel[3])
    if len(colors) > 256:
        raise ValueError("Scene exceeds GIF's 256-color palette; reduce UI colors first.")
    palette = Image.new("P", (1, 1))
    values = [channel for color in sorted(colors) for channel in color]
    palette.putpalette(values + [0] * (768 - len(values)))
    return palette


def actor_position(actor: Actor, sprite: Sprite, time: float) -> tuple[int, int] | None:
    width, height = sprite.size
    if actor.name == "gengar" and time < actor.enter:
        return (WIDTH - width) // 2, actor.feet - height
    if not actor.enter <= time < actor.exit:
        return None
    progress = (time - actor.enter) / (actor.exit - actor.enter)
    start = (WIDTH - width) / 2 if actor.name == "gengar" else -width
    x = round(start + (WIDTH + 12 - start) * progress)
    if actor.name == "dragonite":
        y = 42 + round(3 * sin((time - actor.enter) * pi + actor.phase))
    else:
        y = actor.feet - height - round(2 * abs(sin(time * 9 + actor.phase)))
    return x, y


def render_frame(time: float, background: Image.Image, sprites: dict[str, Sprite]) -> Image.Image:
    image = background.copy()
    # Clip moving sprites to the window interior so they never cover its border/UI.
    scene = Image.new("RGBA", (WIDTH, HEIGHT))
    shadow_draw = ImageDraw.Draw(scene)
    for actor in ACTORS:
        sprite = sprites[actor.name]
        position = actor_position(actor, sprite, time)
        if position is None:
            continue
        x, y = position
        if actor.name != "dragonite":
            width = sprite.size[0]
            shadow_draw.ellipse((x + width // 4, actor.feet - 2,
                                 x + width * 3 // 4, actor.feet + 1), fill="#1c1e2d")
        elapsed = time if time < actor.enter else time - actor.enter + actor.phase
        scene.alpha_composite(sprite.frame_at(elapsed), position)
    image.paste(scene.crop((22, 39, 878, 150)), (22, 39), scene.crop((22, 39, 878, 150)))
    draw = ImageDraw.Draw(image)
    if 2.8 <= time < 12.2:
        x = right_text(draw, 20, "CHAOS DETECTED", RED)
        # Draw the warning icon explicitly: no Unicode/font support is required.
        draw.polygon(((x - 20, 29), (x - 14, 19), (x - 8, 29)), outline=YELLOW)
        draw.line((x - 14, 23, x - 14, 25), fill=YELLOW)
        draw.point((x - 14, 27), fill=YELLOW)
    else:
        right_text(draw, 20, "[ idle ]" if time < 2.8 else "[ sleeping ]", MUTED)
    if 2.0 <= time < 2.8:
        # A tiny pixel alert pops above Gengar, then settles before the escape.
        x, y = WIDTH // 2, 46 - (3 if time < 2.15 else 0)
        draw.rectangle((x - 7, y - 3, x + 7, y + 18), fill="#282432")
        draw.rectangle((x - 5, y - 1, x + 5, y + 16), fill="#30263b")
        draw.rectangle((x - 1, y + 1, x + 1, y + 9), fill=YELLOW)
        draw.rectangle((x - 1, y + 12, x + 1, y + 14), fill=YELLOW)
    return image


def generate() -> None:
    sprites = {actor.name: load_sprite(actor) for actor in ACTORS}
    background = make_background()
    palette = make_palette(background, sprites)
    values = palette.getpalette()
    color_indices = {tuple(values[index:index + 3]): index // 3
                     for index in range(0, len(values), 3)}
    count = FPS * LOOP_MS // 1000
    # GIF durations use 10 ms units; alternate 60/70 ms for exactly 16 FPS / 16 s.
    ticks = [round(index * 1000 / FPS / 10) * 10 for index in range(count + 1)]
    frames = []
    for tick in ticks[:-1]:
        rgb = render_frame(tick / 1000, background, sprites)
        # Map exact colors ourselves: Pillow's nearest-color quantizer caches
        # similar RGB values and can alter even colors already in the palette.
        frame = Image.frombytes("P", rgb.size, bytes(
            color_indices[pixel] for pixel in rgb.get_flattened_data()))
        frame.putpalette(values)
        frames.append(frame)
    durations = [end - start for start, end in zip(ticks, ticks[1:])]
    # Every rendered frame is opaque. Delta rectangles replace old sprite pixels;
    # retaining the previous canvas avoids blank flashes and needless full frames.
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=1, optimize=False)
    with Image.open(OUTPUT) as result:
        duration = sum(frame.info["duration"] for frame in ImageSequence.Iterator(result))
        print(f"{OUTPUT.relative_to(ROOT)}: {result.size[0]}x{result.size[1]}, "
              f"{result.n_frames} encoded frames, {duration / 1000:g}s, "
              f"loop={result.info.get('loop')}, {OUTPUT.stat().st_size / 1024:.1f} KiB")


if __name__ == "__main__":
    generate()
