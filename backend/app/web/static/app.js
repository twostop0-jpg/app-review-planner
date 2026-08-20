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

const STAGE_NAME_ZH = {
  scope: "确定分析范围",
  collect: "采集评论",
  clean: "清洗与结构化",
  analyze: "分类与分析",
  plan: "生成 PRD 与版本计划",
  testcases: "生成测试用例",
  validate: "校验追溯链",
};

const STATUS_ZH = {
  pending: "等待中",
  running: "进行中",
  done: "完成",
  error: "错误",
  skipped: "已跳过",
  queued: "排队中",
  succeeded: "成功",
  failed: "失败",
};

sourceEl.addEventListener("change", () => {
  importWrap.hidden = sourceEl.value !== "import";
});

rawBtn.addEventListener("click", () => {
  showRaw = !showRaw;
  rawBox.hidden = !showRaw;
  rawBtn.textContent = showRaw ? "隐藏 JSON" : "显示 JSON";
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

function statusLabel(status) {
  return STATUS_ZH[status] || status || "等待中";
}

function stageLabel(stage) {
  return STAGE_NAME_ZH[stage.key] || stage.name || stage.key;
}

function renderStages(job) {
  if (!job) {
    stagesBox.innerHTML = `<p class="muted">还没有任务。点击「开始分析」开始。</p>`;
    return;
  }
  const stages = (job.stages || [])
    .map(
      (s) => `
      <li class="stage-item">
        <div class="stage-head">
          <strong>${esc(stageLabel(s))}</strong>
          <span class="${statusClass(s.status)}">${esc(statusLabel(s.status))}</span>
        </div>
        ${s.message ? `<p class="stage-msg">${esc(s.message)}</p>` : ""}
      </li>`
    )
    .join("");
  stagesBox.innerHTML = `
    <p>总体状态：
      <span class="${statusClass(job.status)}">${esc(statusLabel(job.status))}</span>
    </p>
    <ul class="stage-list">${stages}</ul>
  `;
}

function renderFindings(findings) {
  if (!findings?.length) {
    findingsBox.innerHTML = `<p class="muted">暂无问题发现。</p>`;
    return;
  }
  findingsBox.innerHTML = `<ul class="result-list">${findings
    .map(
      (f) => `
    <li class="result-item">
      <div class="result-head">
        <strong>${esc(f.finding_id)}: ${esc(f.title)}</strong>
        <span class="pill">严重度：${esc(f.severity)}</span>
      </div>
      <p class="result-body">${esc(f.summary)}</p>
      <p class="meta-line">支持数=${esc(f.support_count)} · 置信度=${esc(f.confidence)}${
        f.assumption ? " · 含假设" : ""
      }</p>
      <p class="meta-line">关联评论：${esc((f.evidence_review_ids || []).join(", ") || "—")}</p>
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
        `<li><strong>${esc(v.version)}</strong>：${esc(v.focus)}（需求：${esc(
          (v.req_ids || []).join(", ") || "无"
        )}）</li>`
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
      <p class="meta-line">用户问题：${esc(r.user_problem || "—")}</p>
      <p class="meta-line">关联发现：${esc((r.linked_finding_ids || []).join(", ") || "—")}</p>
      <p class="meta-line">关联评论：${esc((r.linked_review_ids || []).join(", ") || "—")}</p>
    </li>`
    )
    .join("");
  prdBox.innerHTML = `
    <h3 style="margin:0 0 8px;font-size:1.05rem">${esc(prd.title || "")}</h3>
    <p class="result-body">${esc(prd.background || "")}</p>
    ${versions ? `<p class="meta-line">版本拆分：</p><ul class="simple-list">${versions}</ul>` : ""}
    <ul class="result-list">${reqs}</ul>
  `;
}

function renderTestcases(testcases) {
  if (!testcases?.length) {
    tcBox.innerHTML = `<p class="muted">暂无测试用例。</p>`;
    return;
  }
  tcBox.innerHTML = `<ul class="result-list">${testcases
    .map(
      (tc) => `
    <li class="result-item">
      <div class="result-head">
        <strong>${esc(tc.tc_id)}: ${esc(tc.title)}</strong>
        <span class="pill">${esc(tc.priority)}${
          tc.origin === "rule" ? " · 规则兜底" : ""
        }</span>
      </div>
      <p class="result-body">${esc(tc.objective)}</p>
      <ol class="steps">${(tc.steps || [])
        .map((s) => `<li>${esc(s)}</li>`)
        .join("")}</ol>
      <p class="meta-line">期望结果：${esc(tc.expected_result || "—")}</p>
      <p class="meta-line">关联需求：${esc(
        (tc.linked_req_ids || []).join(", ") || "—"
      )} · 关联评论：${esc((tc.linked_review_ids || []).join(", ") || "—")}</p>
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
    <p>校验状态：
      <span class="${statusClass(validation.ok ? "succeeded" : "failed")}">
        ${validation.ok ? "通过" : "存在问题"}
      </span>
    </p>
    <p class="meta-line">
      评论=${esc(s.reviews)} · 发现=${esc(s.findings)} · 需求=${esc(s.requirements)} ·
      用例=${esc(s.testcases)} · 已覆盖需求=${esc(s.covered_requirements)}
    </p>
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
    errorBox.textContent = `任务错误：${job.error}`;
  }
}

async function createJob() {
  const source = sourceEl.value;
  const body = {
    app_url: document.getElementById("appUrl").value.trim(),
    goal: document.getElementById("goal").value.trim() || null,
    source,
    import_path:
      source === "import" ? document.getElementById("importPath").value.trim() : null,
  };
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`创建任务失败（${res.status}）：${await res.text()}`);
  }
  const data = await res.json();
  return data.job_id;
}

async function getJob(jobId) {
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(`查询任务失败（${res.status}）：${await res.text()}`);
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
        startBtn.textContent = "开始分析";
      }
    } catch (err) {
      stopPolling();
      startBtn.disabled = false;
      startBtn.textContent = "开始分析";
      errorBox.textContent = err.message || String(err);
    }
  }, 1000);
}

startBtn.addEventListener("click", async () => {
  errorBox.textContent = "";
  startBtn.disabled = true;
  startBtn.textContent = "分析中…";
  stopPolling();
  try {
    const jobId = await createJob();
    jobMeta.textContent = `任务 ID：${jobId}`;
    const first = await getJob(jobId);
    renderJob(first);
    startPolling(jobId);
  } catch (err) {
    startBtn.disabled = false;
    startBtn.textContent = "开始分析";
    errorBox.textContent = err.message || String(err);
  }
});
