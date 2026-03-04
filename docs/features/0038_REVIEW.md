# Feature 0038 Code Review: Real-time Dashboard Sync via WebSocket

## Verdict
Status: Approved with minor follow-up.

## Findings (ordered by severity)

### [P3] Unauthenticated endpoint test does not verify required close code
- **File:** `tests/realtime/test_websocket.py:170`
- **Issue:** `test_endpoint_rejects_unauthenticated()` asserts only that an exception is raised, but does not assert close code `4401`.
- **Impact:** A regression to a different close code (or handshake behavior) could pass tests while violating the feature contract.
- **Recommendation:** Assert `WebSocketDisconnect.code == 4401` (or equivalent TestClient-specific close-code assertion).

## Resolved Since Previous Review
- ✅ `src/realtime/manager.py` now iterates over a snapshot (`list(connections)`) to avoid concurrent set-mutation runtime errors.
- ✅ `frontend/src/composables/useRealtimeSync.js` now suppresses reconnect for terminal auth/policy close codes (`4401`, `1008`).
- ✅ Endpoint-level WebSocket tests were added in `tests/realtime/test_websocket.py` (authenticated connect, ping, disconnect cleanup).
- ✅ Unawaited coroutine warnings in websocket tests are resolved.

## Plan Implementation Checklist

| Requirement | Status | Notes |
| --- | --- | --- |
| Create `src/realtime/manager.py` | ✅ | Implemented with connect/disconnect/notify singleton |
| Create `src/realtime/websocket.py` | ✅ | Auth + endpoint + ping loop implemented |
| Include ws router in FastAPI app | ✅ | `src/api/main.py` includes router |
| Route `/ws/` to FastAPI in ASGI multiplexer | ✅ | `asgi.py` adds `"/ws/"` prefix; websocket scopes route by path |
| Trigger notifications in habit service completion/revert paths | ✅ | Added in all three service methods with exception isolation |
| Integrate frontend composable into Dashboard | ✅ | `Dashboard.vue` now calls `useRealtimeSync()` |
| Frontend auto-reconnect exponential backoff | ✅ | 1s→16s cap implemented |
| Endpoint-level websocket tests from plan | ✅ | Integration tests added using `TestClient` |
| Frontend tests from plan | ⚪ | Not implemented (optional in plan wording) |

## Data Alignment Review
No snake_case/camelCase or payload-shape mismatch found in the implemented message contract. Backend sends `{"type": "dashboard_update"}` and frontend reads `data.type === "dashboard_update"`.

## Over-Engineering / File Size
No over-engineering concerns. New modules are small and focused.

## Validation Performed
- `uv run ruff check asgi.py src/api/main.py src/services/habit_service.py src/realtime/manager.py src/realtime/websocket.py tests/realtime/test_manager.py tests/realtime/test_websocket.py tests/realtime/test_service_notifications.py` (passed)
- `uv run pytest tests/realtime/test_manager.py tests/realtime/test_websocket.py tests/realtime/test_service_notifications.py` (23 passed)
- `uv run pytest -q tests/test_habit_service.py` (passed)
