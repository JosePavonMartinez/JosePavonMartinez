The profile renders `assets/pokemon-parade.gif`, an opaque, self-contained
900 × 190 animation. Its 16-second loop runs at 16 FPS during motion; identical
frames, including the empty final pause, are merged when encoding.

Regenerate from the repository root:

```sh
python -m pip install -r requirements.txt
python scripts/generate_pokemon_parade.py
```

The script also works from other directories. It reads the six checked-in GIFs
in `assets/pokemon/` and needs no network access or installed fonts. Pillow is
pinned so repeated runs use the same renderer and GIF encoder. Source frames
retain their original timing and transparency; scaling uses nearest-neighbor.
An exact, shared palette preserves sprite colors without dithering.

Adjust `ACTORS` to change sizes, entrance/exit times, or ground placement. Gengar
idles until 2.8 s, reacts at 2 s, then escapes. Pikachu, Charmander, Squirtle,
and Bulbasaur enter in order; Dragonite follows above. The scene is empty from
12.2 s until the loop restarts. Increment the parade's `?v=1` in the profile
README after changing its generated GIF to refresh GitHub's cached image.

Sprite source: [PokéAPI/sprites](https://github.com/PokeAPI/sprites), Generation V
Black/White animated front sprites. Local names correspond to these IDs:

| File | ID |
| --- | --- |
| gengar.gif | 94 |
| pikachu.gif | 25 |
| charmander.gif | 4 |
| squirtle.gif | 7 |
| bulbasaur.gif | 1 |
| dragonite.gif | 149 |

Original download pattern:
`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-v/black-white/animated/{ID}.gif`.
The upstream notice is preserved in `assets/pokemon/LICENCE.txt`; image contents
are copyright The Pokémon Company.
