# SID2MIDI Accessible 0.1 — Windows (experimental)

Windows front-end by Lo-lo and ChatGPT for the independent open-source [sid2midi-public](https://github.com/djayuffe/sid2midi-public) engine by djayuffe. The upstream engine is GPL-2.0; preserve upstream copyright and license. This interface is provided under GPL-2.0-or-later. No warranty.

## What it does

- Windows desktop interface using wxPython's native controls, designed for keyboard navigation and NVDA; **screen-reader compatibility has not yet been tested on the user's machine**.
- Open PSID/RSID files, read title and subtune count from the SID header, navigate subtunes with arrow keys and a numeric spinner.
- Convert one song or all songs, select output folder, capture duration, loop detection, and MIDI BPM grid.
- Captures the conversion log, supports cancellation. MUS files are also accepted; the subtune count cannot be read from a PSID header in that format.
- Main program and MIDI engine are independent EXEs; keep both EXEs together in the extracted folder.

## Build on GitHub

1. Create a public GitHub repository named `SID2MIDI-Accessible` (or another name).
2. Upload **the contents** of this source archive into the repository root, preserving `.github/workflows/windows.yml`.
3. Go to **Actions > Build Windows > Run workflow** (or push to `main`).
4. When successful, open the run and download the artifact `SID2MIDI-Accessible-Windows-x64`. Extract the ZIP, then launch `SID2MIDI-Accessible.exe`.

GitHub Actions downloads the upstream source during the build and packages the two EXEs. The **first build has not yet been executed**; any upstream changes or runner changes may require adjustments. For a reproducible release, pin the upstream repository to a tested commit instead of its moving `main` branch.

## Notes

- MIDI note timing is derived from SID emulation, not from audio transcription. Pitch bend and CC are exported by the engine.
- MIDI tempo is the *DAW grid setting*; it does not mean that the program estimates the musical BPM of the SID.
- Large SID files and conversion of all subtunes may take significant CPU time.
- Some RSID files depend on original Commodore ROM images. The upstream GitHub project does not ship those ROMs; refer to upstream README. Not every SID is guaranteed to convert correctly.
- This preliminary package does not create a GitHub Release automatically; the workflow publishes a downloadable build artifact.

## Sources and licensing

The GUI source is `app.py`. Upstream sources are downloaded from the public project during CI, and included with the built package. Keep GPL licensing and attribution for redistributions.
