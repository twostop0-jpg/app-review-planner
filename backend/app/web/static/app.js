const sourceEl = document.getElementById("source");
const importWrap = document.getElementById("importWrap");
const startBtn = document.getElementById("startBtn");
const jobMeta = document.getElementById("jobMeta");
const errorBox = document.getElementById("errorBox");
const stagesBox = document.getElementById("stagesBox");
const findingsBox = document.getElementById("findingsBox");
const prdBox = document.getElementById("prdBox");
const tcBox = document.getElementById("tcBox");
const valBox = document.getElementById("valBox");
const rawBox = document.getElementById("rawBox");
const rawBtn = document.getElementById("rawBtn");

let pollTimer = null;
let showRaw = false;

sourceEl.addEventListener("change", () => {
  importWrap.hidden = sourceEl.value !== "import";
});

rawBtn.addEventListener("click", () => {
  showRaw = !showRaw;
  rawBox.hidden = !showRaw;
  rawBtn.textContent = showRaw ? "Hide JSON" : "Show JSON";
});

function esc(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function statusClass(status) {
  return `status status-${status || "pending"}`;
}

function renderStages(job) {
  if (!job) {
    stagesBox.innerHTML = `<p class="muted">还没有任务。点击 Start 开始。</p>`;
    return;
  }
  const stages = (job.stages || [])
    .map(
      (s) => `
      <li class="stage-item">
        <div class="stage-head">
          <strong>${esc(s.name)}</strong>
          <span class="${statusClass(s.status)}">${esc(s.status)}</span>
        </div>
        ${s.message ? `<p class="stage-msg">${esc(s.message)}</p>` : ""}
      </li>`
    )
    .join("");
  stagesBox.innerHTML = `
    <p>Overall status:
      <span class="${statusClass(job.status)}">${esc(job.status)}</span>
    </p>
    <ul class="stage-list">${stages}</ul>
  `;
}

function renderFindings(findings) {
  if (!findings?.length) {
    findingsBox.innerHTML = `<p class="muted">暂无 findings。</p>`;
    return;
  }
  findingsBox.innerHTML = `<ul class="result-list">${findings
    .map(
      (f) => `
    <li class="result-item">
      <div class="result-head">
        <strong>${esc(f.finding_id)}: ${esc(f.title)}</strong>
        <span class="pill">${esc(f.severity)}</span>
      </div>
      <p class="result-body">${esc(f.summary)}</p>
      <p class="meta-line">support=${esc(f.support_count)} · confidence=${esc(f.confidence)}${f.assumption ? " · assumption" : ""}</p>
      <p class="meta-line">reviews: ${esc((f.evidence_review_ids || []).join(", ") || "—")}</p>
    </li>`
    )
    .join("")}</ul>`;
}

function renderPrd(prd) {
  if (!prd || (!prd.title && !(prd.requirements || []).length)) {
    prdBox.innerHTML = `<p class="muted">暂无 PRD。</p>`;
    return;
  }
  const versions = (prd.version_plan || [])
    .map(
      (v) =>
        `<li><strong>${esc(v.version)}</strong>: ${esc(v.focus)} (${esc(
          (v.req_ids || []).join(", ") || "none"
        )})</li>`
    )
    .join("");
  const reqs = (prd.requirements || [])
    .map(
      (r) => `
    <li class="result-item">
      <div class="result-head">
        <strong>${esc(r.req_id)}: ${esc(r.title)}</strong>
        <span class="pill">${esc(r.priority)} · ${esc(r.version)}</span>
      </div>
      <p class="result-body">${esc(r.description)}</p>
      <p class="meta-line">findings: ${esc((r.linked_finding_ids || []).join(", ") || "—")}</p>
      <p class="meta-line">reviews: ${esc((r.linked_review_ids || []).join(", ") || "—")}</p>
    </li>`
    )
    .join("");
  prdBox.innerHTML = `
    <h3 style="margin:0 0 8px;font-size:1.05rem">${esc(prd.title || "")}</h3>
    <p class="result-body">${esc(prd.background || "")}</p>
    ${versions ? `<ul class="simple-list">${versions}</ul>` : ""}
    <ul class="result-list">${reqs}</ul>
  `;
}

function renderTestcases(testcases) {
  if (!testcases?.length) {
    tcBox.innerHTML = `<p class="muted">暂无 test cases。</p>`;
    return;
  }
  tcBox.innerHTML = `<ul class="result-list">${testcases
    .map(
      (tc) => `
    <li class="result-item">
      <div class="result-head">
        <strong>${esc(tc.tc_id)}: ${esc(tc.title)}</strong>
        <span class="pill">${esc(tc.priority)}${tc.origin === "rule" ? " · fallback" : ""}</span>
      </div>
      <p class="result-body">${esc(tc.objective)}</p>
      <ol class="steps">${(tc.steps || [])
        .map((s) => `<li>${esc(s)}</li>`)
        .join("")}</ol>
      <p class="meta-line">expected: ${esc(tc.expected_result || "—")}</p>
      <p class="meta-line">reqs: ${esc((tc.linked_req_ids || []).join(", ") || "—")} · reviews: ${esc(
        (tc.linked_review_ids || []).join(", ") || "—"
      )}</p>
    </li>`
    )
    .join("")}</ul>`;
}

function renderValidation(validation) {
  if (!validation || typeof validation !== "object") {
    valBox.innerHTML = `<p class="muted">暂无追溯结果。</p>`;
    return;
  }
  const s = validation.summary || {};
  valBox.innerHTML = `
    <p>Status: <span class="${statusClass(validation.ok ? "succeeded" : "failed")}">${
      validation.ok ? "OK" : "ISSUES"
    }</span></p>
    <p class="meta-line">reviews=${esc(s.reviews)} · findings=${esc(s.findings)} · requirements=${esc(
    s.requirements
  )} · testcases=${esc(s.testcases)} · covered=${esc(s.covered_requirements)}</p>
    ${(validation.notes || []).map((n) => `<p class="result-body">${esc(n)}</p>`).join("")}
  `;
}

function renderJob(job) {
  renderStages(job);
  const a = job.artifacts || {};
  renderFindings(a.findings);
  renderPrd(a.prd);
  renderTestcases(a.testcases);
  renderValidation(a.validation);
  rawBox.textContent = JSON.stringify(a, null, 2);
  if (job.error) {
    errorBox.textContent = `Job error: ${job.error}`;
  }
}

async function createJob() {
  const source = sourceEl.value;
  const body = {
    app_url: document.getElementById("appUrl").value.trim(),
    goal: document.getElementById("goal").value.trim() || null,
    source,
    import_path: source === "import" ? document.getElementById("importPath").value.trim() : null,
  };
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Create job failed (${res.status}): ${await res.text()}`);
  }
  const data = await res.json();
  return data.job_id;
}

async function getJob(jobId) {
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(`Get job failed (${res.status}): ${await res.text()}`);
  }
  return res.json();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function startPolling(jobId) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const job = await getJob(jobId);
      renderJob(job);
      if (job.status === "succeeded" || job.status === "failed") {
        stopPolling();
        startBtn.disabled = false;
        startBtn.textContent = "Start";
      }
    } catch (err) {
      stopPolling();
      startBtn.disabled = false;
      startBtn.textContent = "Start";
      errorBox.textContent = err.message || String(err);
    }
  }, 1000);
}

startBtn.addEventListener("click", async () => {
  errorBox.textContent = "";
  startBtn.disabled = true;
  startBtn.textContent = "Running...";
  stopPolling();
  try {
    const jobId = await createJob();
    jobMeta.textContent = `Job ID: ${jobId}`;
    const first = await getJob(jobId);
    renderJob(first);
    startPolling(jobId);
  } catch (err) {
    startBtn.disabled = false;
    startBtn.textContent = "Start";
    errorBox.textContent = err.message || String(err);
  }
});
