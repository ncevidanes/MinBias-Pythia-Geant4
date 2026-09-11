# Operational and failure contracts

This document defines the runtime, output-publication, interruption,
failure, and recovery contracts of `PythiaGeantOneStage`.

It documents observable guarantees of the current implementation.
It intentionally does not claim guarantees that are not implemented
or validated.

## 1. Successful execution

A successful simulation terminates with exit status `0`.

The requested ROOT output becomes visible under its final pathname
during the publication phase at the end of a successful run.

The resolved configuration manifest is retained as:

```text
<output>.manifest.txt
```

The final ROOT file and its manifest represent a completed published
run.

## 2. Transactional ROOT output

Simulation output is first written to a staging file located in the
same directory as the requested final output.

For a final output such as:

```text
run.root
```

the staging pathname is:

```text
.run.root.partial.root
```

The final output pathname is not used as the active ROOT file while
event processing is in progress.

Publication occurs only after simulation event processing has
completed and the application enters the commit phase.

## 3. Publication contract

The output transaction uses `std::filesystem::rename` to move the
staging file to the requested final pathname.

Publication therefore changes the visible ROOT pathname only at the
transaction commit stage.

The implementation does not use a copy-and-delete publication
sequence.

The manifest is not renamed together with the ROOT file. It is
created under its final manifest pathname and retained only after
successful completion of the transaction.

## 4. Controlled failure before publication

Before commit, the output transaction guard owns the staging ROOT
file and manifest.

If execution leaves the transaction scope without successful commit,
the guard performs best-effort cleanup of:

```text
<staging ROOT file>
<output>.manifest.txt
```

A controlled failure before publication therefore must not expose an
incomplete ROOT file under the requested final ROOT pathname.

Cleanup is best-effort because the process and operating system must
still be capable of executing the guard destructor.

## 5. SIGINT and SIGTERM

The application installs handlers for:

- `SIGINT`;
- `SIGTERM`.

The signal handler does not perform simulation cleanup directly.

Its responsibility is limited to recording the signal through
lock-free atomic state while interruption is still accepted.

The handler must not perform operations such as:

- dynamic allocation;
- C++ stream output;
- filesystem operations;
- ROOT operations;
- Geant4 operations;
- exception throwing.

Those restrictions are part of the signal-safety contract.

## 6. Cooperative interruption

Interruption is cooperative rather than asynchronous cleanup from the
signal handler.

During event processing, an accepted interruption request is observed
at an event boundary.

At the end of an event, the application can request:

```text
AbortRun(true)
```

from the Geant4 run manager.

Control subsequently returns through the normal application flow,
where the recorded interruption is converted into a controlled
failure.

This design keeps filesystem and simulation-framework operations out
of the asynchronous signal handler.

## 7. Exit status for controlled interruption

For an interruption recorded before the commit phase, the application
returns:

```text
128 + signal_number
```

Therefore the controlled interruption contracts are:

| Signal | Signal number | Application exit status |
|---|---:|---:|
| `SIGINT` | 2 | 130 |
| `SIGTERM` | 15 | 143 |

These exit statuses apply to interruptions recorded and handled by the
application.

They are not a general promise for arbitrary external process
termination.

## 8. Commit linearization point

The application defines the beginning of the commit phase as the
linearization point for interruption semantics.

Signals recorded before that point may suppress publication and lead
to the controlled interruption path.

Once the commit phase has begun, newly delivered `SIGINT` or `SIGTERM`
signals are not recorded as cancellation requests by the application.

This avoids a late cancellation request ambiguously racing with output
publication.

## 9. SIGKILL and abrupt process death

`SIGKILL` cannot be caught, blocked, or converted into application
cleanup by the process.

The same limitation applies to abrupt termination that prevents normal
C++ stack unwinding or operating-system write completion.

Consequently, after `SIGKILL`, power loss, kernel failure, hardware
failure, or equivalent abrupt termination, the application does not
guarantee automatic cleanup of staging or manifest files.

A residual file such as:

```text
.run.root.partial.root
```

can therefore remain on disk.

A residual manifest can also remain.

No application-level exit-status contract is defined here for
`SIGKILL`.

## 10. Manual recovery after abrupt termination

Before recovering files from an interrupted run, first verify that no
active `PythiaGeantOneStage` process is still using the target output.

Then inspect:

```text
<output>
.<output filename>.partial.root
<output>.manifest.txt
```

If the final ROOT output is absent but staging or manifest artifacts
remain, those artifacts represent an unpublished or incompletely
cleaned transaction.

Preserve them first if they are required for diagnosis or forensic
inspection.

Otherwise they may be removed explicitly, for example:

```bash
rm -f -- .run.root.partial.root run.root.manifest.txt
```

A new production run should use a clean and unique output pathname.

A residual staging file must not be interpreted as a successfully
published simulation result.

## 11. Pre-existing output protection

Before starting a transaction, the implementation validates that the
following transaction paths do not already exist:

- requested final ROOT output;
- staging ROOT output;
- manifest.

If any of them already exists, transaction initialization fails.

This protects normal sequential operation from accidentally starting
on top of an existing transaction artifact.

This check must not be interpreted as a cross-process locking
mechanism.

## 12. Manifest contract

The manifest records the resolved configuration associated with the
run.

It is written before event processing and remains available after a
successful transaction.

During a controlled failure before publication, the transaction guard
attempts to remove it together with the staging ROOT file.

After abrupt process death, its presence alone is not evidence that
the ROOT output was successfully published.

The final ROOT pathname remains the publication indicator.

## 13. ROOT metadata ownership

Run metadata is written by the output layer for event identifier `0`.

This establishes a single event-owned metadata record for the run and
avoids duplicating the run configuration for every simulated event.

The metadata contains configuration and provenance information used to
associate output data with the conditions under which the run was
produced.

## 14. Filesystem atomicity and durability

The current publication implementation uses
`std::filesystem::rename`.

The staging file is deliberately created in the same parent directory
as the final output, avoiding a normal cross-filesystem publication
path.

However, namespace publication and crash durability are different
properties.

The current implementation does not perform an explicit durability
protocol based on operations such as:

```text
fsync(staging file)
fsync(parent directory)
```

Therefore this project does not claim that successful rename is
durable against every possible power-loss or storage-failure
scenario.

The contract is transactional publication during normal process and
filesystem operation, not a crash-consistent storage transaction.

## 15. Concurrent writers and TOCTOU limitation

The implementation checks whether transaction paths exist before the
simulation starts.

Publication occurs later.

There is therefore a time interval between the initial existence
check and the final rename operation.

The current implementation does not use an operating-system primitive
equivalent to:

```text
renameat2(..., RENAME_NOREPLACE)
```

and does not implement an inter-process output lock.

Consequently, multiple processes must not intentionally target the
same final output pathname concurrently.

Unique output names are an operational requirement.

The pre-existing-file checks protect normal sequential use but must
not be described as a race-free no-replace guarantee between
independent processes.

## 16. Partial-result policy

Only the final published ROOT pathname represents a completed output
transaction.

A staging ROOT file is not an official simulation result.

For a controlled failure before commit, expected behavior is:

```text
final ROOT output: absent
staging ROOT output: removed on best-effort cleanup
manifest: removed on best-effort cleanup
exit status: failure
```

For abrupt termination such as `SIGKILL`, residual staging and
manifest artifacts may remain and require manual inspection or
cleanup.

The project does not promote residual staging data into an official
partial-result format.

## 17. Operator checklist

Before a production run:

1. use a unique output pathname;
2. verify that final, staging, and manifest paths do not already exist;
3. retain sufficient free storage for the simulation;
4. use controlled `SIGINT` or `SIGTERM` when interruption is necessary;
5. avoid `SIGKILL` unless immediate forced termination is required.

After a non-zero exit:

1. record the process exit status;
2. inspect whether the final ROOT pathname exists;
3. inspect staging and manifest artifacts;
4. preserve residual files if failure diagnosis is required;
5. remove stale artifacts before reusing the same output pathname.

A final ROOT file should be treated as published output only according
to the transaction behavior described in this document.

## 18. Scope

This document is an operational and technical contract.

It covers:

- output transaction behavior;
- controlled interruption;
- failure cleanup;
- signal exit statuses;
- abrupt termination limitations;
- stale-artifact recovery;
- filesystem publication limitations;
- concurrency limitations.

Release engineering, repository presentation, scientific publication,
DOI preparation, and public-facing project polish remain outside the
scope of Cycle 13.7.
