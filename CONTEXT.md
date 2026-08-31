# Vector Archive Context

This context defines the language used when identifying and archiving inactive file vectors, and for the store-level maintenance of the same index.

## Language

**File Vector State**:
The authoritative current state of a file's Main Chunk Vector Index. Each successfully indexed file has exactly one state record, containing no vector or chunk content.
_Avoid_: Archive status, file registry, lifecycle event

**Main Chunk Vector Index**:
The file-level collection of chunk vectors used by the primary retrieval and archive flows. QA, summary, and other derived indexes are not part of it.

**Available Vector Index**:
A complete vector index that is currently available for retrieval and may become an Archive Candidate after sufficient inactivity.
_Avoid_: Restored state

**Archiving Vector Index**:
A Main Chunk Vector Index currently being transferred from active vector storage to archive storage.

**Indexing Vector Index**:
A Main Chunk Vector Index currently being created or replaced and therefore not yet available for retrieval or archival.

**Archived Vector Index**:
A vector index whose active vector data has been moved to archive storage and is unavailable for normal retrieval until restored.

**Vector Archive Object**:
The single file-level object in durable object storage that contains every chunk vector required to restore one Archived Vector Index.
_Avoid_: Archive row, vector backup, archive detail

**Archive Storage**:
The durable object storage that owns Vector Archive Objects. Relational storage records File Vector State but does not store archived chunk or vector content.
_Avoid_: Archive table

**Vector Index State Record**:
The single File Vector State record for a file. It exists only while the file has a Main Chunk Vector Index and is removed when that index is permanently deleted.
_Avoid_: Failure history, deletion audit

**Index Completion**:
The successful completion of the entire vector-indexing operation for a file. Partial chunk persistence is not Index Completion.

**Vector Restoration**:
The successful return of an Archived Vector Index to active vector storage. It produces an Available Vector Index and begins a new inactivity period.
_Avoid_: Restored state

**Archive Candidate**:
A file that currently satisfies the inactivity and archive-status rules for vector archival.

**Archive Preview**:
A point-in-time, read-only view of all current Archive Candidates. It neither reserves candidates nor guarantees that a later archive run will process the same files.
_Avoid_: Simulation, reservation

**Vector Index Rebuild**:
The store-level operation that rebuilds the vector index of the Main Chunk Vector Index collection in the vector store. While it runs, the collection does not accept vector writes or deletes, so no file can reach Index Completion and no vector deletion can take effect until it finishes. It is distinct from per-file re-indexing and from Index Completion.
_Avoid_: Reindex, per-file rebuild, Index Completion

**Ingestion Suspension**:
The operational state, entered before a Vector Index Rebuild and exited after it completes, in which new Main Chunk Vector Index vector writes and deletions are not applied. Changes requested while suspended are deferred in the message queue and applied after the suspension ends; they are never silently dropped.
_Avoid_: consumer switch, env flag, maintenance mode
