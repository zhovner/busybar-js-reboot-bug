# BUSY Bar reboots when a JS app calls `fetch()` after `clearInterval()` in the same interval callback

## Summary

A JS app that calls `fetch()` from inside a `setInterval` callback **after** calling
`clearInterval()` on that same interval reboots the whole device within about a second.
Calling the same two functions in the opposite order works fine.

## Device

| | |
|---|---|
| Model | BB.1 |
| Firmware | 1.3.1 (branch 1.3.1, build 2026-10-26, commit `8edd2da4`) |
| HTTP API | 27.14.0 |
| Connection | Wi-Fi, API access mode `key` |

## Minimal repro

`app.repro.reboot/scripts/main.js`, the whole app:

```js
const timer = setInterval(() => {
  clearInterval(timer);
  fetch("http://localhost/api/version");
}, 100);
```

Control, `app.repro.control/scripts/main.js` (same calls, opposite order, no reboot):

```js
const timer = setInterval(() => {
  fetch("http://localhost/api/version");
  clearInterval(timer);
}, 100);
```

## Steps

Using `repro.py` (Python 3, standard library only):

```bash
python3 repro.py <busybar-ip> <api-key> app.repro.reboot
python3 repro.py <busybar-ip> <api-key> app.repro.control
```

The script packs the app folder into a `.tgz`, then stages, installs and launches it over the HTTP API. It
compares `boot_time` from `GET /api/status/system` before and after, and uninstalls the app at the end.

To do it by hand instead: pack the folder with `tar czf app.tgz app.repro.reboot`, upload it in the web interface, and start it.

## Expected

The app runs once and exits. The device stays up.

## Actual

```
app.repro.reboot   ->  RESULT: REBOOTED   (HTTP API unreachable ~1 s after launch, uptime resets)
app.repro.control  ->  RESULT: no reboot
```

Every run of a crashing variant rebooted the device (9 of 9 runs). Nothing about the crash shows up in the log: the in-memory log is
lost on reboot, and `POST /api/log_dump` snapshots taken just before it show only
`[JsRunner] Running script: .../main.js`.

## What we narrowed down

| Variant | Result |
|---|---|
| `clearInterval(timer)` then `fetch(...)` in the same callback | **reboot** |
| `fetch(...)` then `clearInterval(timer)` | ok |
| `clearInterval(timer)` then `setTimeout(...)`, with no fetch | ok |
| `clearInterval(timer)` then `setTimeout(() => fetch(...), 50)` | ok (our workaround) |
| 10 fps draw loop (`POST /api/display/draw`), then `clearInterval` and `DELETE /api/display/draw` from the same callback | **reboot** |
| Same loop, but the final request waits for the in-flight draw (requests strictly one at a time) | **reboot** |
| The same `DELETE /api/display/draw`, called from a `setTimeout` | ok |

So it's not specific to the endpoint, the HTTP method, the request body, or two requests running at once. The trigger is
starting a `fetch` from inside the callback of an interval that has already been cleared. It looks like the cleared
timer's context is freed while the callback is still running, and a native call made after that point uses it.

## Workaround

Do the cleanup requests from a fresh timer:

```js
clearInterval(timer);
setTimeout(() => { fetch(...); }, 10);
```

## Another finding (minor)

`POST /api/audio/play` with a `path` that doesn't exist in the app's assets returns `200 {"result":"OK"}`.
Then `DELETE /api/audio/play` also returns 200, as if something were playing. The OpenAPI spec says
`404 Audio file not found or is unplayable`.

```bash
curl -X POST -H "X-API-Token: <key>" -H 'Content-Type: application/json' \
  -d '{"application_name":"no_such_app","path":"sounds/missing.snd"}' http://<busybar-ip>/api/audio/play
# -> 200 {"result":"OK"}
```
