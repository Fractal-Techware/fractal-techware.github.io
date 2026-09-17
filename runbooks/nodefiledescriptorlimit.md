---
title: "NodeFileDescriptorLimit: runbook and fix"
description: "NodeFileDescriptorLimit means a host is close to the kernel-wide open file limit. How to find the process leaking file descriptors and fix it."
permalink: /runbooks/nodefiledescriptorlimit/
breadcrumb: {title: Alert runbooks, url: /runbooks/}
domain: Hosts (node_exporter)
severity: warning
cta:
  title: Get this alert, tested
  text: "NodeFileDescriptorLimit is one of 25 host alerts in the pack of 179, each with promtool unit tests and a full runbook."
  button: See the alert pack
  url: https://fractaltechware.gumroad.com/l/prometheus-alert-rules-pack?utm_source=site&utm_medium=runbook&utm_campaign=nodefiledescriptorlimit
  free: https://github.com/Fractal-Techware/prometheus-alert-rules
---
# NodeFileDescriptorLimit

The host has allocated most of the file handles the kernel allows system-wide, and new files and sockets will soon fail to open.

| | |
|---|---|
| Severity | warning |
| Source | node_exporter 1.x, `filefd` collector (reads `/proc/sys/fs/file-nr`) |
| Key metrics | `node_filefd_allocated`, `node_filefd_maximum` |

## What it means

Every open file, socket, pipe and eventfd uses a kernel file handle. `node_filefd_maximum` is `fs.file-max`, the system-wide ceiling, and `node_filefd_allocated` is how many are in use. The alert fires when usage has stayed close to that ceiling for a sustained period.

When the limit is reached, `open()`, `accept()` and `socket()` fail with "Too many open files in system" (ENFILE). Web servers stop accepting connections, databases cannot open files, and even SSH logins can fail. This is different from a single process hitting its own `ulimit -n` (EMFILE), which this alert does not measure.

## Common causes

- A file descriptor leak: an application opens sockets or files and never closes them.
- Connection storms: very high numbers of client or upstream connections, often in `CLOSE_WAIT`.
- A deliberately low `fs.file-max` from an old sysctl tuning file.
- Many containers or processes on a dense node each holding thousands of handles.
- Log shippers or file watchers tracking deleted-but-still-open files.

## First checks

1. Watch the trend; a steady climb suggests a leak, a spike suggests load:
   ```promql
   node_filefd_allocated / node_filefd_maximum
   ```
2. Confirm on the host (allocated, unused, max):
   ```bash
   cat /proc/sys/fs/file-nr
   sysctl fs.file-max
   ```
3. Find the processes holding the most descriptors:
   ```bash
   for p in /proc/[0-9]*; do
     echo "$(ls "$p/fd" 2>/dev/null | wc -l) $(cat "$p/comm" 2>/dev/null) ${p#/proc/}"
   done | sort -rn | head -10
   ```
4. Inspect the top offender to see what kind of handles they are:
   ```bash
   sudo lsof -p <pid> | awk '{print $5}' | sort | uniq -c | sort -rn
   ss -tanp | grep -c CLOSE-WAIT
   ```
5. For Go and Java services that expose `process_open_fds`, graph it over time to confirm a leak.

## Fixing it

Short term, restart the leaking process to release its handles, or raise the ceiling with `sysctl -w fs.file-max=<value>` and persist it in `/etc/sysctl.d/`. Modern kernels already set a large default, so a low value is worth questioning. The real fix for a leak is in the application: close connections, set idle timeouts, and use bounded connection pools.

## Related alerts

- [NodeConntrackLimit](/runbooks/nodeconntracklimit/): connection storms often exhaust conntrack at the same time.
- [NodeMemoryHighUtilization](/runbooks/nodememoryhighutilization/): very large handle counts consume kernel memory.
- [NodeFilesystemAlmostOutOfFiles](/runbooks/nodefilesystemalmostoutoffiles/): inode exhaustion gives similar "cannot create file" errors.
