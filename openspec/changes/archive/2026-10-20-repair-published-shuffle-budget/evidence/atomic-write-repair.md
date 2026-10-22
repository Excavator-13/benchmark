# Windows atomic publication repair

2026-10-20, Asia/Shanghai. Development implementation evidence, not independent
verification. Runtime: pinned Python 3.11.17, Windows.

`RunDirectory.write_bytes` used by both entries now retries only Windows
PermissionError WinError 5/32/33. It renames the same flushed temp file, never
repeats computation, and permits eight attempts with seven bounded sleeps
(0.02, 0.04, 0.08, 0.16, 0.25, 0.25, 0.25 seconds). Recovery appends an event;
permanent failure raises while preserving old target and new temp bytes.
Other errors fail immediately. Other numerical save methods are unchanged.

An actual CreateFileW reader with read/write sharing but without delete sharing
reproduces replacement denial; releasing it after 80 ms permits publication.
This establishes the Windows sharing failure mechanism, not the identity of
the process holding the historical matrix04 file. No attribution to antivirus
or an editor is established.

Command at repository root, PYTHONUTF8=1:
`.venv-pinned/Scripts/python.exe -B -m unittest
benchmark.graph_value_skeleton.tests.test_atomic_writes -v`.
Initial focused result: four tests pass, 0.266 seconds. Tests cover transient
same-temp retry, permanent bounded failure/preservation, unrelated immediate
error, and the actual live Windows reader. Final full-suite results are recorded
separately. Original matrix04 checkpoint/failure evidence remains unchanged.
