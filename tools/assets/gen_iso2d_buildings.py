"""Paint the eight city tiers from the deterministic geometry guides (OpenAI images/edits).

The original buildings sheet was generated free form: no guide, no projection
contract, so the tiers landed at different scales, off the tile centre, and
spilled below the tile diamond. Here the geometry is fixed first by
build_iso2d_buildings.py and the model is only allowed to repaint the faces.

The key is images/edits with input_fidelity=high and background=transparent:
a magenta plate contaminates the paint (measured: olive-yellow cast) and the
model adds a soft drop shadow into the key, which then survives chroma removal
and breaks the no-spill rule.

Auth: OPENAI_API_KEY from the environment. Never echo it.
"""
import argparse
import base64
import io
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'originals/iso2d'
GUIDES = BASE / 'guides/buildings'
RAW = BASE / 'raw'
ENDPOINT = 'https://api.openai.com/v1/images/edits'
MODEL = 'gpt-image-1'
CANVAS = 1024

SUBJECT = {
    'water': 'a Han-period Chinese river stockade (水寨): a plank deck on timber piles over water, '
             'two wattle-and-daub huts with thatched roofs, a stilted watchtower, a gangway and '
             'two moored wooden river craft. No masonry and no city wall',
    'garrison': 'a Han-period Chinese field camp (營寨): five ridged canvas army tents and a larger '
                'command tent inside a lashed timber palisade, with crossed defensive stakes and '
                'one timber watchtower. No masonry and no tiled roof',
    'pass': 'a Han-period Chinese pass fortress (關城) blocking a defile: one long stone wall '
            'across the gorge with a crenellated parapet, a two-storey timber gate tower over the '
            'gate, buttressed towers at both ends and a banner. Not a square enclosure',
    'tribal': 'a non-Han frontier camp of the Han period: three round felt tents (ger) and a '
              'cooking fire inside a lashed timber palisade, no masonry and no tiled roof',
    'county-small': 'a small Han-dynasty Chinese county seat (縣): a low mud-brick perimeter wall '
                    'with a plain plank gate and two modest tile-roofed houses inside',
    'county': 'a Han-dynasty Chinese county seat (縣): a rammed-earth wall with a crenellated '
              'parapet, one corner watchtower, a roofed gate and a county office with a granary',
    'commandery': 'a Han-dynasty Chinese commandery seat (郡): a rammed-earth wall with a '
                  'crenellated parapet, two corner watchtowers, a roofed gate tower and a '
                  'commandery office on a stone plinth',
    'commandery-mid': 'a middling Han-dynasty Chinese commandery seat (郡): a rammed-earth wall '
                      'with a crenellated parapet, three corner watchtowers, a roofed gate tower '
                      'and a commandery office with three outbuildings',
    'commandery-major': 'a large Han-dynasty Chinese commandery seat (郡): a high rammed-earth '
                        'wall with a crenellated parapet, four corner watchtowers, a two-storey '
                        'gate tower and a great hall on a stone plinth',
    'commandery-grand': 'a great Han-dynasty Chinese commandery seat (郡): a high rammed-earth '
                        'wall with a crenellated parapet, four corner watchtowers, a two-storey '
                        'gate tower with an inner barbican, and a two-storey great hall',
    'capital': 'the Han-dynasty Chinese imperial capital: a high rammed-earth wall with a '
               'crenellated parapet, four corner watchtowers, paired que gate pillars, a raised '
               'palace terrace with a two-storey throne hall, and one banner',
}

PROMPT = (
    'STRICT GEOMETRY-PRESERVING texture painting task. The attached RGBA image is a 2:1 isometric '
    'massing guide of {subject}, on a fully transparent background. Keep EVERY silhouette, '
    'footprint, wall line, roof ridge, tower position and vertex coordinate EXACTLY as given. Do '
    'not move, rescale, rotate, add or remove any structure. Do not change the camera angle or the '
    'light direction (sun from the upper right: right-facing faces lit, left-facing faces in '
    'shade). Repaint the flat faces as hand-painted semi-realistic historical strategy-game art: '
    'rammed-earth walls with horizontal lift courses and worn edges, fired clay roof tiles with '
    'ridge caps and eave tiles, timber posts and gate leaves, packed-earth courtyard. Hold this '
    'exact muted palette - loess walls #a48869 lit and #6d5b46 in shade, roof tile #564639, timber '
    '#6b543c, courtyard earth #8a7457, foliage dark olive #55603a. No yellow-green cast, no '
    'saturated colour. Not pixel art. The background must stay FULLY TRANSPARENT: no ground '
    'diamond, no soil pedestal, no tile base, no drop shadow, no glow, no outline, no text, no '
    'labels, no grid. Nothing may extend beyond the existing silhouette, and nothing at all below '
    'its bottom edge.'
)


def _multipart(fields, image_bytes):
    boundary = '----iso2d' + uuid.uuid4().hex
    out = []
    for name, value in fields.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                   f'{value}\r\n'.encode())
    out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; '
               f'filename="guide.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
    out.append(image_bytes)
    out.append(f'\r\n--{boundary}--\r\n'.encode())
    return b''.join(out), boundary


def paint(tier):
    guide = Image.open(GUIDES / f'{tier}.png').convert('RGBA')
    # nearest keeps the guide's hard face boundaries; a smooth upscale invites
    # the model to round the corners it is told to preserve.
    plate = io.BytesIO()
    guide.resize((CANVAS, CANVAS), Image.Resampling.NEAREST).save(plate, 'PNG')
    body, boundary = _multipart({
        'model': MODEL, 'prompt': PROMPT.format(subject=SUBJECT[tier]),
        'size': f'{CANVAS}x{CANVAS}', 'input_fidelity': 'high',
        'background': 'transparent', 'output_format': 'png', 'n': '1',
    }, plate.getvalue())
    request = urllib.request.Request(ENDPOINT, data=body, headers={
        'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'],
        'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(request, timeout=900) as response:
        payload = json.load(response)
    data = base64.b64decode(payload['data'][0]['b64_json'])
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f'buildings-{tier}.png').write_bytes(data)
    (BASE / 'prompts' / f'buildings-{tier}.txt').write_text(
        PROMPT.format(subject=SUBJECT[tier]) + '\n')
    return dict(tier=tier, bytes=len(data), usage=payload.get('usage'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tiers', nargs='*', default=sorted(SUBJECT))
    args = parser.parse_args()
    if not os.environ.get('OPENAI_API_KEY'):
        raise SystemExit('OPENAI_API_KEY is not set')
    for name in args.tiers:
        print(json.dumps(paint(name), ensure_ascii=False))
