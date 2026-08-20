const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8001";

export async function createJob({
  appUrl,
  goal,
  source = "sample",
  importPath = null,
}) {
  const response = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      app_url: appUrl,
      goal: goal || null,
      source,
      import_path: source === "import" ? importPath : null,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Create job failed (${response.status}): ${text}`);
  }

  const data = await response.json();
  return data.job_id;
}

export async function getJob(jobId) {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Get job failed (${response.status}): ${text}`);
  }
  return response.json();
}
