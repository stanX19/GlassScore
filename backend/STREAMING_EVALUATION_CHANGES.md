# Streaming Evaluation API Changes

## Overview

The evaluation system has been **decoupled** to separate evaluation triggering from result streaming. This provides better modularity and allows clients to control when to start evaluation and when to consume results independently.

---

## Key Changes

### 1. **Decoupled Evaluation Start and Streaming**
- Previously: Single endpoint triggered evaluation AND streamed results
- Now: Separate endpoints for starting evaluation (`/start`) and consuming results (`/stream`)
- Benefit: Better separation of concerns, evaluation can be triggered without immediately consuming results

### 2. **New Event Types**
- Added `event_type` field to all `EvaluationEvidence` objects
- Values:
  - `"evaluation_start"` - Signals evaluation has begun
  - `"evidence"` - Regular evaluation evidence (default)
  - `"evaluation_complete"` - Signals that initial evaluation tasks have finished

### 3. **Stream Stays Open Indefinitely**
- Stream remains open after `evaluation_complete` event
- Continues listening for re-evaluation results automatically
- Only closes on client disconnect or error
- Benefit: Re-evaluation results appear in same stream without reconnecting

### 4. **Evidence Invalidation Triggers Re-evaluation**
- When `POST /evidence/update` is called with `valid: false`, a background LLM task is spawned
- This task analyzes the invalidation and generates NEW evidence (typically score 0 or +2)
- New evidence is pushed to the session queue automatically
- Original evidence remains in the list (not replaced)
- Benefit: Can open new stream to receive re-evaluation results

---

## API Changes

### `POST /evaluate/start` (NEW)

**Purpose:** Triggers evaluation process without streaming results

**Request:**
```json
{
  "session_id": 123
}
```

**Response:**
```json
{
  "message": "Evaluation started",
  "session_id": 123
}
```

**Behavior:**
- Checks if evaluation is already in progress (returns 400 if yes)
- Starts evaluation tasks in background (ML, LLM, Web)
- Returns immediately without waiting for results
- Results are queued in session for later streaming

**Error Codes:**
- `404`: Session not found
- `400`: Evaluation already in progress

---

### `POST /evaluate/stream`

**Purpose:** Streams evaluation results from session queue

**Request:**
```json
{
  "session_id": 123
}
```

**Behavior:**
- Opens SSE connection to stream queued evidence
- Can be called anytime - before, during, or after evaluation
- **Stays open indefinitely** to receive re-evaluation results
- Evidence is automatically saved to session's `evidence_list` during streaming
- Only closes on client disconnect or error

**Response Stream:**
```
data: {"score": 0, "description": "Evaluation started", "event_type": "evaluation_start", ...}

data: {"id": 1, "score": 50, "description": "ML Model Score", "event_type": "evidence", ...}

data: {"id": 2, "score": -5, "description": "Gambling mentions found", "event_type": "evidence", ...}

data: {"id": 3, "score": 2, "description": "Stable employment verified", "event_type": "evidence", ...}

data: {"score": 0, "description": "Initial evaluation completed", "event_type": "evaluation_complete", ...}

[stream stays open, waiting for more evidence...]

[user invalidates evidence #2 via POST /evidence/update]

data: {"id": 4, "score": 0, "description": "Re-assessed: Context was misunderstood", "source": "original evaluation", "event_type": "evidence", ...}
```

**Error Codes:**
- `404`: Session not found

### `POST /evidence/update`

**Request:**
```json
{
  "session_id": 123,
  "evidence_id": 2,
  "valid": false,
  "invalidate_reason": "This evidence misinterpreted the context"
}
```

**Behavior:**
- Updates the evidence's `valid` and `invalidate_reason` fields
- If `valid: false`, spawns background LLM re-evaluation task
- Re-evaluation result is **automatically pushed to the active stream**
- Returns updated session immediately (doesn't wait for re-evaluation)

**New Evidence Properties:**
- `source`: `"Re-evaluation of Evidence #<original_id>"`
- `event_type`: `"evidence"`
- `score`: Typically 0 or +2 (corrective assessment)
- Gets new `id` and is added to `evidence_list`

---

## Frontend Implementation Guide

### 1. **Two-Step Process: Start Then Stream**

```javascript
// Step 1: Start evaluation (non-blocking)
async function startEvaluation(sessionId) {
  const response = await fetch('/evaluate/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId })
  });
  
  if (!response.ok) {
    const error = await response.json();
    if (response.status === 400) {
      console.log('Evaluation already in progress');
    }
    throw new Error(error.detail);
  }
  
  return response.json();
}

// Step 2: Stream results
function streamEvaluationResults(sessionId) {
  const eventSource = new EventSource(`/evaluate/stream?session_id=${sessionId}`);
  
  eventSource.onmessage = (event) => {
    const evidence = JSON.parse(event.data);
    
    if (evidence.event_type === 'evaluation_start') {
      console.log('Evaluation started');
      showLoadingSpinner();
    } else if (evidence.event_type === 'evaluation_complete') {
      console.log('Initial evaluation completed');
      hideLoadingSpinner();
      showCompletionBadge();
      // DON'T close stream - keep it open for re-evaluation results
    } else if (evidence.event_type === 'evidence') {
      addEvidenceToUI(evidence);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    eventSource.close();
  };
  
  return eventSource;
}

// Usage: Start evaluation and keep stream open
await startEvaluation(sessionId);
const stream = streamEvaluationResults(sessionId);

// Stream stays open to receive re-evaluation results automatically
// No need to close or reopen when invalidating evidence
```

### 2. **Display Re-evaluation Evidence**

Re-evaluation evidence has distinctive properties:

```javascript
function addEvidenceToUI(evidence) {
  const isReEvaluation = evidence.source.startsWith('Re-evaluation of Evidence #');
  
  if (isReEvaluation) {
    // Optionally highlight or badge re-evaluated evidence
    const originalId = evidence.source.match(/#(\d+)/)[1];
    
    // You might want to:
    // - Show it with a "Re-evaluated" badge
    // - Link it to the original invalidated evidence
    // - Animate it into view to catch user attention
    
    displayEvidenceCard(evidence, { 
      badge: 'Re-evaluated',
      linkedTo: originalId,
      highlight: true 
    });
  } else {
    displayEvidenceCard(evidence);
  }
}
```

### 3. **Handle Completion Event**

```javascript
function handleEvaluationComplete() {
  document.getElementById('status').textContent = 'Evaluation complete';
  document.getElementById('spinner').style.display = 'none';
  
  showToast('You can now invalidate evidence. Re-evaluations will generate new evidence.');
}
```

### 4. **Invalidate Evidence**

```javascript
async function invalidateEvidence(evidenceId, reason) {
  const response = await fetch('/evidence/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: currentSessionId,
      evidence_id: evidenceId,
      valid: false,
      invalidate_reason: reason
    })
  });
  
  if (response.ok) {
    // Update UI to show evidence as invalidated
    markEvidenceAsInvalid(evidenceId, reason);
    showReEvaluationPending(evidenceId);
    
    // No need to open new stream!
    // Re-evaluation results will appear in existing open stream automatically
  }
}
```

---

## Example Flow

### Initial Evaluation

1. **User starts evaluation:**
   - Frontend: `POST /evaluate/start` with `session_id`
   - Backend: Returns immediately, starts evaluation in background

2. **User opens stream:**
   - Frontend: `POST /evaluate/stream` with `session_id`
   - Backend: Opens SSE connection, streams queued results

3. **Evidence streams in:**
   - Frontend receives `evaluation_start` event
   - Frontend receives evidence as tasks complete
   - Each added to UI dynamically

4. **Initial evaluation completes:**
   - Frontend receives `evaluation_complete` event
   - Updates UI (hide spinner, show completion)
   - **Stream automatically closes**

### Re-evaluation Flow

5. **User invalidates evidence #2:**
   - Frontend: `POST /evidence/update` with `valid: false`
   - Backend: Updates evidence, spawns LLM re-evaluation task in background
   - Backend: Pushes new evidence to session queue when ready

6. **Re-evaluation appears automatically:**
   - Frontend receives new evidence via **existing open SSE stream**
   - No need to reconnect or poll - stream is still listening
   - Source: Original evidence source (preserved from invalidated evidence)
   - Display with special styling/badge based on description or source

---

## Migration Checklist

- [ ] Split evaluation triggering: Use `POST /evaluate/start` instead of only `/stream`
- [ ] Update streaming: Call `POST /evaluate/stream` separately after start
- [ ] Handle new `evaluation_start` event type
- [ ] Handle `evaluation_complete` event type  
- [ ] **DON'T close stream** after completion event - keep it open for re-evaluations
- [ ] Add UI for displaying re-evaluated evidence
- [ ] Add visual distinction for re-evaluations (badge, highlight)
- [ ] Show loading state when user invalidates evidence
- [ ] Handle SSE reconnection on errors
- [ ] Consider showing link between invalidated evidence and its re-evaluation
- [ ] Test that evaluation can start without immediately streaming
- [ ] Test that re-evaluation results appear in existing stream automatically

---

## Notes

- **Breaking Change**: Clients must now call `/start` before `/stream` (or call both)
- **Flexibility**: Can start evaluation without streaming (e.g., background processing)
- **Modularity**: Evaluation logic fully decoupled from streaming mechanism
- **Performance**: Backend handles unlimited concurrent LLM re-evaluations
- **Connection Management**: Stream auto-closes after completion, open new one for re-evaluations
- **Error Handling**: Re-evaluation errors are sent as evidence with `score: 0` and error description
- **Queue Persistence**: Evidence queue persists in memory, can be streamed multiple times

---

## Questions?

If you need clarification on any of these changes, please reach out to the backend team.
