# Source inventory and state production

New original work, MIT; see LICENSE-NOTICE.md and ../../exports/naval-v1/NOTICE.txt.

Native source IDs: scout.blend, warship.blend, transport.blend, river-narrow.blend, estuary.blend, lake.blend, coastal-port.blend.

The three ship scenes preserve the complete 3D hull, UVs, planked deck, mast, sail, battens, oars and class details. All four state geometries (including fire/smoke and tow rope) are stored together, hidden where not in use. tools/naval-v1/blender_pipeline.py toggles/animates these actual objects and rotates the root to produce the direction/state frames. No sprite is painted over a screenshot. The persistent neutral scene is saved before render; render always reloads that native scene.

textures/wood.png and textures/sail.png are new deterministic 32×32 author textures, not downloads. Their images are externally preserved with relative //textures references. Do not flatten the sources into one screenshot or delete invisible state objects.

Each board is a distinct mesh with 4096 row-major tile faces, matching the native navalVisualRows property and reviewed exported visualRows. Fixed shore/shallows/port geometry is original art, not a retexture of a land map. Runtime/legal depth and topology remain backend-owned.

See ../../docs/naval-v1.md for regeneration commands, projection coordinates, manifest fields, inventory, state combinations, legal source-pin boundary and real execution evidence policy. Preview images do not prove product execution.
