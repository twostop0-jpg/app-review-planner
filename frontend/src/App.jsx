import { useEffect, useRef, useState } from "react";
import { createJob, getJob } from "./api";
import "./App.css";

const DEFAULT_URL =
  "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684";

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

function statusClass(status) {
  return `status status-${status || "pending"}`;
}

function statusLabel(status) {
  return STATUS_ZH[status] || status || "等待中";
}

function stageLabel(stage) {
  return STAGE_NAME_ZH[stage.key] || stage.name || stage.key;
}

function Section({ title, children, empty }) {
  if (empty) {
    return (
      <section className="panel">
        <h2>{title}</h2>
        <p className="muted">暂无数据。</p>
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
    return <Section title="问题发现（Findings）" empty />;
  }
  return (
    <Section title="问题发现（Findings）">
      <ul className="result-list">
        {findings.map((f) => (
          <li key={f.finding_id} className="result-item">
            <div className="result-head">
              <strong>
                {f.finding_id}: {f.title}
              </strong>
              <span className="pill">严重度：{f.severity}</span>
            </div>
            <p className="result-body">{f.summary}</p>
            <p className="meta-line">
              支持数={f.support_count} · 置信度={f.confidence}
              {f.assumption ? " · 含假设" : ""}
            </p>
            <p className="meta-line">
              关联评论：{(f.evidence_review_ids || []).join(", ") || "—"}
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function PrdPanel({ prd }) {
  if (!prd?.requirements?.length && !prd?.title) {
    return <Section title="PRD / 版本计划" empty />;
  }
  return (
    <Section title="PRD / 版本计划">
      {prd.title ? <h3 className="subhead">{prd.title}</h3> : null}
      {prd.background ? <p className="result-body">{prd.background}</p> : null}
      {prd.version_plan?.length ? (
        <div className="block">
          <h4 className="tiny-head">版本拆分</h4>
          <ul className="simple-list">
            {prd.version_plan.map((v) => (
              <li key={v.version}>
                <strong>{v.version}</strong>：{v.focus}
                {v.req_ids?.length ? `（${v.req_ids.join(", ")}）` : ""}
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
            <p className="meta-line">用户问题：{r.user_problem || "—"}</p>
            <p className="meta-line">
              关联发现：{(r.linked_finding_ids || []).join(", ") || "—"}
            </p>
            <p className="meta-line">
              关联评论：{(r.linked_review_ids || []).join(", ") || "—"}
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function TestcasesPanel({ testcases }) {
  if (!testcases?.length) {
    return <Section title="测试用例" empty />;
  }
  return (
    <Section title="测试用例">
      <ul className="result-list">
        {testcases.map((tc) => (
          <li key={tc.tc_id} className="result-item">
            <div className="result-head">
              <strong>
                {tc.tc_id}: {tc.title}
              </strong>
              <span className="pill">
                {tc.priority}
                {tc.origin === "rule" ? " · 规则兜底" : ""}
              </span>
            </div>
            <p className="result-body">{tc.objective}</p>
            <ol className="steps">
              {(tc.steps || []).map((step, i) => (
                <li key={`${tc.tc_id}-s${i}`}>{step}</li>
              ))}
            </ol>
            <p className="meta-line">期望结果：{tc.expected_result || "—"}</p>
            <p className="meta-line">
              关联需求：{(tc.linked_req_ids || []).join(", ") || "—"} · 关联评论：
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
    return <Section title="追溯校验" empty />;
  }
  const summary = validation.summary || {};
  return (
    <Section title="追溯校验">
      <p>
        校验状态：{" "}
        <span className={statusClass(validation.ok ? "succeeded" : "failed")}>
          {validation.ok ? "通过" : "存在问题"}
        </span>
      </p>
      <p className="meta-line">
        评论={summary.reviews ?? "—"} · 发现={summary.findings ?? "—"} · 需求=
        {summary.requirements ?? "—"} · 用例={summary.testcases ?? "—"} ·
        已覆盖需求={summary.covered_requirements ?? "—"}
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
        <h1>评论洞察规划器</h1>
        <p className="subtitle">
          美区 App Store 评论 → 问题发现 → PRD/版本计划 → 测试用例（全链路可追溯）
        </p>
      </header>

      <section className="panel">
        <label className="label">
          App Store 链接
          <input
            className="input"
            value={appUrl}
            onChange={(e) => setAppUrl(e.target.value)}
            placeholder="https://apps.apple.com/us/app/..."
          />
        </label>

        <label className="label">
          分析目标（可选）
          <input
            className="input"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="例如：提升留存与计费清晰度"
          />
        </label>

        <label className="label">
          数据来源
          <select
            className="input"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="sample">样例数据（离线演示）</option>
            <option value="live">实时采集（美区 App Store）</option>
            <option value="import">导入文件（JSON/CSV）</option>
          </select>
        </label>

        {source === "import" ? (
          <label className="label">
            导入路径（相对仓库根目录）
            <input
              className="input"
              value={importPath}
              onChange={(e) => setImportPath(e.target.value)}
              placeholder="data/imports/example_reviews.csv"
            />
          </label>
        ) : null}

        <button className="button" onClick={handleStart} disabled={loading || !appUrl}>
          {loading ? "分析中…" : "开始分析"}
        </button>

        {jobId ? <p className="meta">任务 ID：{jobId}</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {job?.error ? <p className="error">任务错误：{job.error}</p> : null}
      </section>

      <section className="panel">
        <h2>执行阶段</h2>
        {!job ? (
          <p className="muted">还没有任务。点击「开始分析」开始。</p>
        ) : (
          <>
            <p>
              总体状态：{" "}
              <span className={statusClass(job.status)}>{statusLabel(job.status)}</span>
            </p>
            {artifacts.collection_meta?.note ? (
              <p className="meta-line">{artifacts.collection_meta.note}</p>
            ) : null}
            <ul className="stage-list">
              {job.stages.map((stage) => (
                <li key={stage.key} className="stage-item">
                  <div className="stage-head">
                    <strong>{stageLabel(stage)}</strong>
                    <span className={statusClass(stage.status)}>
                      {statusLabel(stage.status)}
                    </span>
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
              <h2>原始结果（JSON）</h2>
              <button
                type="button"
                className="button ghost"
                onClick={() => setShowRaw((v) => !v)}
              >
                {showRaw ? "隐藏 JSON" : "显示 JSON"}
              </button>
            </div>
            {showRaw ? (
              <pre className="code">{JSON.stringify(artifacts, null, 2)}</pre>
            ) : (
              <p className="muted">清洗报告、统计信息等可在原始 JSON 中查看。</p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
