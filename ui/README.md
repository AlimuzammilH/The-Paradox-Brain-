# Paradox brain interface

A Three.js interface that shows Paradox thinking. Each phase the engine streams (frame, atomise, tension, diagnose, synthesise, evaluate, object, recurse, answer) lights up its own part of the brain: claims appear as stars in the left and right hemispheres, contradictions arc between them, candidate syntheses cross the corpus callosum, and the winner ignites as a supernova.

The built interface is one file, `dist/index.html`, and the engine serves it at http://localhost:8100 (`uvicorn paradox.api:app --port 8100`, or `Start Paradox Brain.bat` on Windows). Opened without a running engine it plays a recorded example, labelled DEMO REPLAY. `?api=http://host:port` points it at another engine, and `?demo` forces the replay.

Sound is synthesised in the browser and starts muted; the speaker button turns it on and shows the volume slider.

```bash
npm install
npm run dev      # http://localhost:5173, talks to the engine on :8100
npm run build    # rebuilds dist/index.html
```
