#!/usr/bin/env python3
"""Build and check the /runbooks/ section of the site.

  python3 scripts/runbooks.py free    # (re)generate the 12 free, MIT-licensed runbook pages
  python3 scripts/runbooks.py index   # rebuild runbooks/index.md from the rule catalog
  python3 scripts/runbooks.py check   # verify coverage, front matter, links, no paid rule leakage

Condensed pages for the other alerts are hand-written in runbooks/<alertname-lowercase>.md.
Paths to the pack and the free repo can be overridden with PACK_DIR and FREE_DIR.
"""
import glob
import os
import re
import sys

import yaml

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.environ.get("PACK_DIR", os.path.join(SITE, "..", "..", "prometheus-alert-rules-pack", "pro"))
FREE = os.environ.get("FREE_DIR", os.path.join(SITE, "..", "prometheus-alert-rules-free"))
RB = os.path.join(SITE, "runbooks")
FREE_REPO = "https://github.com/Fractal-Techware/prometheus-alert-rules"
PACK_URL = "https://store.fractaltechware.com/l/prometheus-alert-rules-pack"
INDEX_MARKER_START = "<!-- RUNBOOK_INDEX:START -->"
INDEX_MARKER_END = "<!-- RUNBOOK_INDEX:END -->"

FREE_DESCRIPTIONS = {
    "KubePodCrashLooping": "KubePodCrashLooping runbook: read the previous container logs, exit codes and events, find why the pod keeps restarting and fix it.",
    "KubePodNotReady": "KubePodNotReady runbook: why a pod is stuck Pending, Unknown or Failed (scheduling, PVCs, nodes) and the kubectl checks to fix it.",
    "KubeContainerOOMKilled": "KubeContainerOOMKilled runbook: confirm the OOM kill, compare memory usage to the limit, and decide between raising limits or fixing a leak.",
    "KubeImagePullBackOff": "KubeImagePullBackOff runbook: diagnose wrong image tags, missing imagePullSecrets, registry auth and rate limits, then fix the pull.",
    "KubeDeploymentReplicasMismatch": "KubeDeploymentReplicasMismatch runbook: why a Deployment has fewer available replicas than desired and how to get them back.",
    "KubeDeploymentRolloutStuck": "KubeDeploymentRolloutStuck runbook: a rollout exceeded progressDeadlineSeconds. Find the failing new pods, then roll back or fix forward.",
    "KubeNodeNotReady": "KubeNodeNotReady runbook: check kubelet, container runtime, disk and network on a NotReady Kubernetes node and recover or replace it.",
    "NodeExporterDown": "NodeExporterDown runbook: tell a dead host from a stopped node_exporter or a broken scrape, with the checks for each case.",
    "NodeFilesystemSpaceFillingUp": "NodeFilesystemSpaceFillingUp runbook: find what is filling the disk (du, deleted open files, logs, images) before it hits 100%.",
    "NodeFilesystemAlmostOutOfSpace": "NodeFilesystemAlmostOutOfSpace runbook: a filesystem has under 10% (warning) or 5% (critical) free. Free space fast and safely.",
    "NodeHighCPUUsage": "NodeHighCPUUsage runbook: find the processes or pods burning CPU on a host above 90% and decide whether to throttle, scale or fix.",
    "NodeMemoryHighUtilization": "NodeMemoryHighUtilization runbook: find what is using host memory above 90%, check for leaks and avoid the OOM killer.",
}

INDEX_INTRO = """Mid-incident and staring at an unfamiliar alert name? Each page below explains what a common Prometheus alert means in plain words, what usually causes it, and the first commands to run (kubectl, PromQL, shell) to find out what is actually wrong.

The alerts come from the [Prometheus Alert Rules & Runbook Pack]({pack}?utm_source=site&utm_medium=runbook&utm_campaign=index): {total} alerts across {domains} domains, every one covered by promtool unit tests. {free} of them, with their rules, tests and full runbooks, are free under MIT in [prometheus-alert-rules on GitHub]({repo}); those pages are marked *free rule*."""


def slug(alert):
    return alert.lower()


def load_catalog():
    """Return (ordered list of alerts, domain order) from the pack's rules and catalog."""
    cat = open(os.path.join(PACK, "alert-catalog.md")).read()
    domains = []  # (file slug, domain name)
    for m in re.finditer(r"^\| ([^|]+) \| `rules/([a-z-]+)\.rules\.yml` \|", cat, re.M):
        domains.append((m.group(2), m.group(1).strip()))
    free = {
        os.path.basename(p)[:-3]
        for p in glob.glob(os.path.join(FREE, "runbooks", "*", "*.md"))
        if not p.endswith("README.md")
    }
    alerts = {}
    order = []
    for fslug, dname in domains:
        doc = yaml.safe_load(open(os.path.join(PACK, "rules", fslug + ".rules.yml")))
        for g in doc["groups"]:
            for r in g["rules"]:
                if "alert" not in r:
                    continue
                a = alerts.get(r["alert"])
                if a is None:
                    a = alerts[r["alert"]] = {
                        "alert": r["alert"], "file": fslug, "domain": dname,
                        "summary": r["annotations"]["summary"], "severities": [],
                        "free": r["alert"] in free, "exprs": [], "fors": [],
                    }
                    order.append(r["alert"])
                if r["labels"]["severity"] not in a["severities"]:
                    a["severities"].append(r["labels"]["severity"])
                a["exprs"].append(r["expr"])
                a["fors"].append(r.get("for", "0m"))
    return [alerts[n] for n in order], domains


def split_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("no front matter")
    return yaml.safe_load(m.group(1)), m.group(2)


def cmd_free():
    alerts, _ = load_catalog()
    by_name = {a["alert"]: a for a in alerts}
    for a in alerts:
        if not a["free"]:
            continue
        name = a["alert"]
        src = open(os.path.join(FREE, "runbooks", a["file"], name + ".md")).read()
        # Drop the repo footer.
        src = re.split(r"\n---\nFree sample of", src)[0].rstrip() + "\n"
        lines = src.split("\n")
        assert lines[0] == "# " + name, name
        summary = lines[2].strip("*")
        body = "\n".join(lines[3:]).lstrip("\n")
        rule_file = "rules/%s.rules.yml" % a["file"]
        body = re.sub(r"\| Rule file \| `rules/[a-z-]+\.rules\.yml`",
                      "| Rule file | [`%s`](%s/blob/main/%s)" % (rule_file, FREE_REPO, rule_file), body)
        head, sep, rule = body.partition("## Rule definition")
        # Link alert names mentioned in prose (outside code) to their pages.
        def link(m):
            n = m.group(0)
            return "[%s](/runbooks/%s/)" % (n, slug(n)) if n in by_name and n != name else n
        names = sorted(by_name, key=len, reverse=True)
        pat = re.compile(r"(?<![\w/\[`])(" + "|".join(names) + r")(?![\w\]`])")
        head = "\n".join(l if l.lstrip().startswith(("```", "kubectl", "sum", "sudo")) else pat.sub(link, l)
                         for l in head.split("\n"))
        if sep:
            rule = (sep + "\n\nFrom [`%s`](%s/blob/main/%s) in the free repository (MIT). "
                    "Unit tests for it are in [`tests/`](%s/tree/main/tests).\n\n{%% raw %%}"
                    % (rule_file, FREE_REPO, rule_file, FREE_REPO)
                    + rule.strip("\n") + "\n{% endraw %}\n")
        related = [x for x in alerts if x["file"] == a["file"] and x["alert"] != name]
        related.sort(key=lambda x: (not x["free"],))
        rel = "\n## Related alerts\n\n" + "\n".join(
            "- [%s](/runbooks/%s/): %s" % (x["alert"], slug(x["alert"]), x["summary"]) for x in related[:5]) + "\n"
        sev = ", ".join(sorted(a["severities"], key=["info", "warning", "critical"].index))
        fm = {
            "title": "%s: runbook and fix" % name,
            "description": FREE_DESCRIPTIONS[name],
            "permalink": "/runbooks/%s/" % slug(name),
            "breadcrumb": {"title": "Alert runbooks", "url": "/runbooks/"},
            "domain": a["domain"],
            "severity": sev,
            "free_rule": True,
            "cta": {
                "title": "Get the other 167 alerts, tested",
                "text": "%s is one of 12 free alerts. The full pack has 179 alerts across 20 domains, each with promtool unit tests and a runbook." % name,
                "button": "See the alert pack",
                "url": "%s?utm_source=site&utm_medium=runbook&utm_campaign=%s" % (PACK_URL, slug(name)),
                "free": FREE_REPO,
            },
        }
        out = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000) + "---\n"
        out += "# %s\n\n%s Free rule (MIT): the complete runbook and rule definition are below.\n\n" % (name, summary)
        out += head.rstrip() + "\n" + rel + "\n" + (rule if sep else "")
        open(os.path.join(RB, slug(name) + ".md"), "w").write(out)
        print("wrote runbooks/%s.md" % slug(name))


def cmd_index():
    alerts, domains = load_catalog()
    path = os.path.join(RB, "index.md")
    text = open(path).read()
    parts = [INDEX_INTRO.format(pack=PACK_URL, total=179, domains=len(domains),
                                free=sum(a["free"] for a in alerts), repo=FREE_REPO)]
    for fslug, dname in domains:
        parts.append("## %s\n" % dname)
        for a in [x for x in alerts if x["file"] == fslug]:
            sev = " / ".join(sorted(a["severities"], key=["info", "warning", "critical"].index))
            tag = ", *free rule*" if a["free"] else ""
            parts.append("- [%s](/runbooks/%s/): %s (%s%s)" % (a["alert"], slug(a["alert"]), a["summary"], sev, tag))
        parts.append("")
    block = INDEX_MARKER_START + "\n" + "\n\n".join(p for p in parts[:1]) + "\n\n" + "\n".join(parts[1:]).rstrip() + "\n" + INDEX_MARKER_END
    if "<!-- RUNBOOK_INDEX -->" in text:
        text = text.replace("<!-- RUNBOOK_INDEX -->", block)
    else:
        text = re.sub(re.escape(INDEX_MARKER_START) + ".*?" + re.escape(INDEX_MARKER_END), lambda m: block, text, flags=re.S)
    open(path, "w").write(text)
    print("wrote runbooks/index.md")


def norm(s):
    return re.sub(r"\s+", "", s)


def trivial(e):
    """A bare health check like `pg_up == 0`: documented by every exporter, not pack IP."""
    return re.fullmatch(r"[A-Za-z_:][\w:]*(\{[^}]*\})?==[01]", norm(e)) is not None


def cmd_check():
    alerts, _ = load_catalog()
    errors = []
    pages = {}
    for p in sorted(glob.glob(os.path.join(RB, "*.md"))):
        try:
            fm, body = split_front_matter(open(p).read())
        except Exception as e:  # noqa: BLE001
            errors.append("%s: front matter: %s" % (p, e))
            continue
        pages[fm.get("permalink")] = (p, fm, body)
    permalinks = set(pages)
    words = {}
    for a in alerts:
        pl = "/runbooks/%s/" % slug(a["alert"])
        if pl not in pages:
            errors.append("missing page for %s" % a["alert"])
            continue
        p, fm, body = pages[pl]
        if os.path.basename(p) != slug(a["alert"]) + ".md":
            errors.append("%s: filename does not match alert" % p)
        for k in ("title", "description", "breadcrumb", "domain", "severity", "cta"):
            if k not in fm:
                errors.append("%s: missing %s" % (p, k))
        if not str(fm.get("title", "")).startswith(a["alert"] + ":"):
            errors.append("%s: title must start with alert name" % p)
        if len(str(fm.get("description", ""))) > 155:
            errors.append("%s: description is %d chars" % (p, len(fm["description"])))
        if fm.get("domain") != a["domain"]:
            errors.append("%s: domain %r != %r" % (p, fm.get("domain"), a["domain"]))
        cta = fm.get("cta") or {}
        if cta.get("url") != "%s?utm_source=site&utm_medium=runbook&utm_campaign=%s" % (PACK_URL, slug(a["alert"])):
            errors.append("%s: cta.url" % p)
        if not body.lstrip().startswith("# %s\n" % a["alert"]):
            errors.append("%s: body must start with '# %s'" % (p, a["alert"]))
        if not a["free"]:
            if re.search(r"\bexpr:|\bfor:", body):
                errors.append("%s: contains expr:/for:" % p)
            nb = norm(body)
            for e in a["exprs"]:
                if not trivial(e) and norm(e) in nb:
                    errors.append("%s: contains the pack's alert expression" % p)
            if "{{" in body or "{%" in body:
                errors.append("%s: contains Liquid delimiters" % p)
        words[a["alert"]] = len(re.sub(r"```.*?```", " ", body, flags=re.S).split()), len(body.split())
    # Every paid expression must be absent from every non-free page (not just its own).
    paid = [norm(e) for a in alerts if not a["free"] for e in a["exprs"] if len(norm(e)) > 30 and not trivial(e)]
    for pl, (p, fm, body) in pages.items():
        if fm.get("free_rule") or pl == "/runbooks/":
            continue
        nb = norm(body)
        for e in paid:
            if e in nb:
                errors.append("%s: contains a paid alert expression" % p)
    for pl, (p, fm, body) in pages.items():
        for m in re.finditer(r"\]\((/runbooks/[^)#]*)", body):
            if m.group(1) not in permalinks:
                errors.append("%s: broken link %s" % (p, m.group(1)))
    extra = permalinks - {"/runbooks/%s/" % slug(a["alert"]) for a in alerts} - {None}
    idx = [x for x in extra if pages[x][0].endswith("index.md")]
    for x in extra - set(idx):
        errors.append("unexpected page %s" % pages[x][0])
    free_n = sum(a["free"] for a in alerts)
    counts = sorted(v[1] for k, v in words.items() if not next(a for a in alerts if a["alert"] == k)["free"])
    print("alerts: %d unique (%d free full, %d condensed); pages: %d" % (len(alerts), free_n, len(alerts) - free_n, len(pages)))
    if counts:
        print("condensed body words: min %d, median %d, max %d" % (counts[0], counts[len(counts) // 2], counts[-1]))
    short = [k for k, v in words.items() if v[1] < 250]
    long_ = [k for k, v in words.items() if v[1] > 650]
    if short:
        print("short (<250 words):", ", ".join(short))
    if long_:
        print("long (>650 words):", ", ".join(long_))
    for e in errors:
        print("ERROR", e)
    print("OK" if not errors else "%d errors" % len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit({"free": cmd_free, "index": cmd_index, "check": cmd_check}[cmd]() or 0)
