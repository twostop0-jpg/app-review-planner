import { useEffect, useRef, useState } from "react";
import { createJob, getJob } from "./api";
import "./App.css";

const DEFAULT_URL =
  "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684";

function statusClass(status) {
  return `status status-${status || "pending"}`;
}

function Section({ title, children, empty }) {
  if (empty) {
    return (
      <section className="panel">
        <h2>{title}</h2>
        <p className="muted">Not available yet.</p>
      </section>
    );
  }
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function FindingsPanel({ findings }) {
  if (!findings?.length) {
    return <Section title="Findings" empty />;
  }
  return (
    <Section title="Findings">
      <ul className="result-list">
        {findings.map((f) => (
          <li key={f.finding_id} className="result-item">
            <div className="result-head">
              <strong>
                {f.finding_id}: {f.title}
              </strong>
              <span className="pill">{f.severity}</span>
            </div>
            <p className="result-body">{f.summary}</p>
            <p className="meta-line">
              support={f.support_count} · confidence={f.confidence}
              {f.assumption ? " · assumption" : ""} · origin={f.origin}
            </p>
            <p className="meta-line">
              reviews: {(f.evidence_review_ids || []).join(", ") || "—"}
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function PrdPanel({ prd }) {
  if (!prd?.requirements?.length && !prd?.title) {
    return <Section title="PRD / Version plan" empty />;
  }
  return (
    <Section title="PRD / Version plan">
      {prd.title ? <h3 className="subhead">{prd.title}</h3> : null}
      {prd.background ? <p className="result-body">{prd.background}</p> : null}
      {prd.version_plan?.length ? (
        <div className="block">
          <h4 className="tiny-head">Versions</h4>
          <ul className="simple-list">
            {prd.version_plan.map((v) => (
              <li key={v.version}>
                <strong>{v.version}</strong>: {v.focus}
                {v.req_ids?.length ? ` (${v.req_ids.join(", ")})` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <ul className="result-list">
        {(prd.requirements || []).map((r) => (
          <li key={r.req_id} className="result-item">
            <div className="result-head">
              <strong>
                {r.req_id}: {r.title}
              </strong>
              <span className="pill">
                {r.priority} · {r.version}
              </span>
            </div>
            <p className="result-body">{r.description}</p>
            <p className="meta-line">problem: {r.user_problem || "—"}</p>
            <p className="meta-line">
              findings: {(r.linked_finding_ids || []).join(", ") || "—"}
            </p>
            <p className="meta-line">
              reviews: {(r.linked_review_ids || []).join(", ") || "—"}
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function TestcasesPanel({ testcases }) {
  if (!testcases?.length) {
    return <Section title="Test cases" empty />;
  }
  return (
    <Section title="Test cases">
      <ul className="result-list">
        {testcases.map((tc) => (
          <li key={tc.tc_id} className="result-item">
            <div className="result-head">
              <strong>
                {tc.tc_id}: {tc.title}
              </strong>
              <span className="pill">
                {tc.priority}
                {tc.origin === "rule" ? " · fallback" : ""}
              </span>
            </div>
            <p className="result-body">{tc.objective}</p>
            <ol className="steps">
              {(tc.steps || []).map((step, i) => (
                <li key={`${tc.tc_id}-s${i}`}>{step}</li>
              ))}
            </ol>
            <p className="meta-line">expected: {tc.expected_result || "—"}</p>
            <p className="meta-line">
              reqs: {(tc.linked_req_ids || []).join(", ") || "—"} · reviews:{" "}
              {(tc.linked_review_ids || []).join(", ") || "—"}
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function ValidationPanel({ validation }) {
  if (!validation || typeof validation !== "object") {
    return <Section title="Traceability" empty />;
  }
  const summary = validation.summary || {};
  return (
    <Section title="Traceability">
      <p>
        Status:{" "}
        <span className={statusClass(validation.ok ? "succeeded" : "failed")}>
          {validation.ok ? "OK" : "ISSUES"}
        </span>
      </p>
      <p className="meta-line">
        reviews={summary.reviews ?? "—"} · findings={summary.findings ?? "—"} ·
        requirements={summary.requirements ?? "—"} · testcases=
        {summary.testcases ?? "—"} · covered=
        {summary.covered_requirements ?? "—"}
      </p>
      {(validation.notes || []).map((n) => (
        <p key={n} className="result-body">
          {n}
        </p>
      ))}
      {validation.issues?.length ? (
        <pre className="code small">{JSON.stringify(validation.issues, null, 2)}</pre>
      ) : null}
    </Section>
  );
}

export default function App() {
  const [appUrl, setAppUrl] = useState(DEFAULT_URL);
  const [goal, setGoal] = useState("improve retention and billing clarity");
  const [source, setSource] = useState("sample");
  const [importPath, setImportPath] = useState("data/imports/example_reviews.csv");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  function stopPolling() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function startPolling(id) {
    stopPolling();
    timerRef.current = setInterval(async () => {
      try {
        const next = await getJob(id);
        setJob(next);
        if (next.status === "succeeded" || next.status === "failed") {
          stopPolling();
          setLoading(false);
        }
      } catch (err) {
        stopPolling();
        setLoading(false);
        setError(err.message || String(err));
      }
    }, 1000);
  }

  async function handleStart() {
    setError("");
    setJob(null);
    setJobId("");
    setLoading(true);
    setShowRaw(false);
    stopPolling();

    try {
      const id = await createJob({
        appUrl,
        goal,
        source,
        importPath: source === "import" ? importPath : null,
      });
      setJobId(id);
      const first = await getJob(id);
      setJob(first);
      startPolling(id);
    } catch (err) {
      setLoading(false);
      setError(err.message || String(err));
    }
  }

  const artifacts = job?.artifacts || {};

  return (
    <div className="page">
      <header className="header">
        <h1>App Review Planner</h1>
        <p className="subtitle">
          US App Store reviews → findings → PRD → test cases, with full
          traceability.
        </p>
      </header>

      <section className="panel">
        <label className="label">
          App Store URL
          <input
            className="input"
            value={appUrl}
            onChange={(e) => setAppUrl(e.target.value)}
            placeholder="https://apps.apple.com/us/app/..."
          />
        </label>

        <label className="label">
          Analysis goal (optional)
          <input
            className="input"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. subscription conversion, low-rating usability"
          />
        </label>

        <label className="label">
          Data source
          <select
            className="input"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="sample">sample (cached offline demo)</option>
            <option value="live">live (US App Store feeds)</option>
            <option value="import">import (JSON/CSV path)</option>
          </select>
        </label>

        {source === "import" ? (
          <label className="label">
            Import path (repo-relative)
            <input
              className="input"
              value={importPath}
              onChange={(e) => setImportPath(e.target.value)}
              placeholder="data/imports/example_reviews.csv"
            />
          </label>
        ) : null}

        <button className="button" onClick={handleStart} disabled={loading || !appUrl}>
          {loading ? "Running..." : "Start"}
        </button>

        {jobId ? <p className="meta">Job ID: {jobId}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {job?.error ? <p className="error">Job error: {job.error}</p> : null}
      </section>

      <section className="panel">
        <h2>Stages</h2>
        {!job ? (
          <p className="muted">No job yet. Click Start to begin.</p>
        ) : (
          <>
            <p>
              Overall status:{" "}
              <span className={statusClass(job.status)}>{job.status}</span>
            </p>
            {artifacts.collection_meta?.note ? (
              <p className="meta-line">{artifacts.collection_meta.note}</p>
            ) : null}
            <ul className="stage-list">
              {job.stages.map((stage) => (
                <li key={stage.key} className="stage-item">
                  <div className="stage-head">
                    <strong>{stage.name}</strong>
                    <span className={statusClass(stage.status)}>{stage.status}</span>
                  </div>
                  {stage.message ? <p className="stage-msg">{stage.message}</p> : null}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {job ? (
        <>
          <FindingsPanel findings={artifacts.findings} />
          <PrdPanel prd={artifacts.prd} />
          <TestcasesPanel testcases={artifacts.testcases} />
          <ValidationPanel validation={artifacts.validation} />

          <section className="panel">
            <div className="result-head">
              <h2>Raw artifacts</h2>
              <button
                type="button"
                className="button ghost"
                onClick={() => setShowRaw((v) => !v)}
              >
                {showRaw ? "Hide JSON" : "Show JSON"}
              </button>
            </div>
            {showRaw ? (
              <pre className="code">{JSON.stringify(artifacts, null, 2)}</pre>
            ) : (
              <p className="muted">
                Cleaning report, stats, and full payload are available in raw
                JSON.
              </p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
