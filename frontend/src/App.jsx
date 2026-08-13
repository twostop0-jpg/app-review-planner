import { useEffect, useRef, useState } from "react";
import { createJob, getJob } from "./api";
import "./App.css";

const DEFAULT_URL =
  "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684";

function statusClass(status) {
  return `status status-${status || "pending"}`;
}

export default function App() {
  const [appUrl, setAppUrl] = useState(DEFAULT_URL);
  const [goal, setGoal] = useState("subscription conversion");
  const [jobId, setJobId] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
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
    stopPolling();

    try {
      const id = await createJob({ appUrl, goal });
      setJobId(id);
      const first = await getJob(id);
      setJob(first);
      startPolling(id);
    } catch (err) {
      setLoading(false);
      setError(err.message || String(err));
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>App Review Planner</h1>
        <p className="subtitle">
          Day 1 scaffold — start a job and watch the fake analysis pipeline.
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

        <button className="button" onClick={handleStart} disabled={loading || !appUrl}>
          {loading ? "Running..." : "Start"}
        </button>

        {jobId ? <p className="meta">Job ID: {jobId}</p> : null}
        {error ? <p className="error">{error}</p> : null}
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

      <section className="panel">
        <h2>Artifacts</h2>
        <pre className="code">
          {job ? JSON.stringify(job.artifacts, null, 2) : "{}"}
        </pre>
      </section>
    </div>
  );
}
