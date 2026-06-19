"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  ClipboardCheck,
  FileDown,
  FileText,
  GitBranch,
  Landmark,
  Loader2,
  Upload,
  Repeat,
  Scale,
  ShieldCheck,
  UserCheck,
  Users
} from "lucide-react";

type LoanCase = {
  case_id: string;
  borrower_name: string;
  tier: string;
};

type StreamEvent = {
  event: string;
  data: Record<string, unknown>;
};

type AuditEntry = {
  target: string;
  decision: string;
  reviewer: string;
  rationale: string;
  createdAt: string;
};

type EvalResult = {
  summary: {
    overall: Record<string, number>;
    by_tier: Record<string, Record<string, number>>;
  };
  failure_counts: Record<string, number>;
  failures: Array<Record<string, unknown>>;
  risk_confidence_calibration: {
    expected_calibration_error: number;
    buckets: Array<Record<string, unknown>>;
  };
};

type DriftResult = {
  cases: number;
  repeats: number;
  stable_cases: number;
  drifting_cases: number;
  stability_rate: number;
  rows: Array<Record<string, unknown>>;
};

type JudgeResult = {
  cases: number;
  exact_agreement: number;
  within_one_point_agreement: number;
  average_score_delta: number;
  highest_disagreement_dimension: string;
  disagreement_case_count: number;
  manual_spot_check_cases: string[];
};

type PacketJudgeResult = JudgeResult & {
  artifact_name: string;
  characters_extracted: number;
  primary: Record<string, unknown>;
  secondary: Record<string, unknown>;
  dimension_deltas: Record<string, number>;
};

type ProgressState = {
  panel: string;
  label: string;
  completed: number;
  total: number;
  current: string;
  status: "idle" | "running" | "done" | "error";
};

type ActivityLog = {
  panel: string;
  step: string;
  message: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

type Readiness = {
  api: string;
  app: string;
  gold_set_cases: number;
  difficulty_tiers: Record<string, number>;
  llm_mode: boolean;
  live_llm_available: boolean;
  llm_provider: string;
  llm_model: string;
  llm_temperature: number | null;
  primary_judge: string;
  secondary_judge: string;
  live_judges_available: boolean;
  langsmith_tracing: boolean;
  langsmith_project: string;
  live_drift_available: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const API_TIMEOUT_MS = 45000;

const policyOptions = [
  { value: "sba_reviewer", label: "SBA Reviewer" },
  { value: "bank_underwriter", label: "Bank Underwriter" },
  { value: "cdfi_lender", label: "CDFI Lender" }
];

const decisionOptions = [
  "Accept agent finding",
  "Override finding",
  "Request additional evidence",
  "Approve despite finding",
  "Reject despite finding"
];

const tabs = [
  { id: "review", label: "Loan Review", icon: Landmark },
  { id: "evaluation", label: "Evaluation", icon: BarChart3 },
  { id: "ablation", label: "Ablation", icon: Scale },
  { id: "drift", label: "Drift", icon: Repeat },
  { id: "judges", label: "Judge Agreement", icon: Users },
  { id: "report", label: "Report", icon: FileText }
];

export default function Home() {
  const [activeTab, setActiveTab] = useState("review");
  const [cases, setCases] = useState<LoanCase[]>([]);
  const [selectedCase, setSelectedCase] = useState("ADV-001");
  const [policy, setPolicy] = useState("sba_reviewer");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [uploadedReview, setUploadedReview] = useState<Record<string, unknown> | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");
  const [loadingPanel, setLoadingPanel] = useState("");
  const [progressState, setProgressState] = useState<ProgressState | null>(null);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [ablationRows, setAblationRows] = useState<Array<Record<string, unknown>>>([]);
  const [driftResult, setDriftResult] = useState<DriftResult | null>(null);
  const [judgeResult, setJudgeResult] = useState<JudgeResult | null>(null);
  const [packetJudgeResult, setPacketJudgeResult] = useState<PacketJudgeResult | null>(null);
  const [reportText, setReportText] = useState("");
  const [reportPdfReady, setReportPdfReady] = useState(false);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [auditTarget, setAuditTarget] = useState("Outcome - ESCALATE");
  const [auditDecision, setAuditDecision] = useState("Approve despite finding");
  const [auditReviewer, setAuditReviewer] = useState("Human reviewer");
  const [auditRationale, setAuditRationale] = useState(
    "Updated guarantor documentation and verified collateral support justify conditional approval despite the model escalation."
  );
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [readinessError, setReadinessError] = useState("");

  useEffect(() => {
    async function loadInitialState() {
      try {
        const [casesResponse, readinessResponse] = await Promise.all([
          fetch(`${API_BASE}/cases`),
          fetch(`${API_BASE}/readiness`)
        ]);
        if (!casesResponse.ok) {
          throw new Error(`Cases request failed with status ${casesResponse.status}`);
        }
        const payload = (await casesResponse.json()) as LoanCase[];
        setCases(payload);
        if (payload.length > 0 && !payload.some((item) => item.case_id === selectedCase)) {
          setSelectedCase(payload[0].case_id);
        }
        if (readinessResponse.ok) {
          setReadiness((await readinessResponse.json()) as Readiness);
          setReadinessError("");
        } else {
          setReadinessError(`Readiness request failed with status ${readinessResponse.status}`);
        }
      } catch (caught) {
        const message = formatApiError(caught, "/readiness");
        setError(message);
        setReadinessError(message);
      }
    }
    void loadInitialState();
  }, [selectedCase]);

  const completedAgents = useMemo(
    () => events.filter((item) => item.event === "agent_completed"),
    [events]
  );
  const finalEvent = useMemo(
    () => [...events].reverse().find((item) => item.event === "run_completed"),
    [events]
  );
  const activePacket = useMemo(() => {
    const uploadedPacket = uploadedReview?.packet as Record<string, unknown> | undefined;
    const uploadedCase = uploadedReview?.case as Record<string, unknown> | undefined;
    if (uploadedPacket && uploadedCase) {
      return {
        source: "Uploaded document",
        data: uploadedPacket,
        borrower: String(uploadedCase.borrower_name || "Uploaded borrower")
      };
    }
    if (finalEvent) {
      return {
        source: "Gold-set case",
        data: finalEvent.data,
        borrower: ""
      };
    }
    return null;
  }, [finalEvent, uploadedReview]);
  const progress = Math.min(100, Math.round((completedAgents.length / 5) * 100));
  const timelineTargets = useMemo(() => {
    const uploadedTargets = uploadedReview?.audit_targets;
    if (Array.isArray(uploadedTargets) && uploadedTargets.length > 0) {
      return uploadedTargets.map((target) => String(target));
    }
    const finalData = finalEvent?.data;
    const targets = [
      `Outcome - ${String(finalData?.outcome || "PENDING")}`,
      `Risk band - ${String(finalData?.risk || "PENDING")}`
    ];
    if (finalData?.compliance) {
      targets.push(`Compliance status - ${String(finalData.compliance)}`);
    }
    if (finalData?.risk) {
      targets.push(`Risk result - ${String(finalData.risk)}`);
    }
    targets.push("Counterfactual - Improve borrower credit score");
    targets.push("Counterfactual - Supply missing required documents");
    return targets;
  }, [finalEvent, uploadedReview]);
  const activePacketKey = `${activePacket?.source || "empty"}:${String(
    activePacket?.data.case_id || activePacket?.data.outcome || selectedCase
  )}:${String(activePacket?.data.risk || "")}:${String(activePacket?.data.compliance || "")}`;

  useEffect(() => {
    if (!activePacket) {
      return;
    }
    const nextTarget = timelineTargets[0] || "Outcome - PENDING";
    setAuditTarget(nextTarget);
    setAuditDecision(defaultAuditDecision(activePacket.data));
    setAuditRationale(defaultAuditRationale(activePacket));
  }, [activePacket, activePacketKey, timelineTargets]);

  function runPipeline() {
    setEvents([]);
    setUploadedReview(null);
    setAuditEntries([]);
    setError("");
    setIsRunning(true);

    const url = `${API_BASE}/review/stream?case_id=${encodeURIComponent(
      selectedCase
    )}&policy=${encodeURIComponent(policy)}`;
    const source = new EventSource(url);
    const eventNames = ["run_started", "agent_completed", "graph_update", "run_completed", "error"];

    eventNames.forEach((eventName) => {
      source.addEventListener(eventName, (message) => {
        const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
        setEvents((current) => [...current, { event: eventName, data: parsed }]);
        if (eventName === "run_completed" || eventName === "error") {
          source.close();
          setIsRunning(false);
        }
        if (eventName === "error") {
          setError(String(parsed.message || "Pipeline run failed."));
        }
      });
    });

    source.onerror = () => {
      source.close();
      setIsRunning(false);
      setError(`CLARA live stream is not connected. Start the backend, then retry. Endpoint: ${API_BASE}/review/stream`);
    };
  }

  function startProgress(panel: string, label: string, total: number) {
    setProgressState({ panel, label, completed: 0, total, current: "Starting", status: "running" });
  }

  function addActivityLog(panel: string, step: string, message: string, metadata?: Record<string, unknown>) {
    setActivityLogs((current) => [
      {
        panel,
        step,
        message,
        metadata,
        timestamp: new Date().toLocaleTimeString()
      },
      ...current
    ].slice(0, 60));
  }

  function updateProgress(partial: Partial<ProgressState>) {
    setProgressState((current) => (current ? { ...current, ...partial } : current));
  }

  function failProgress(panel: string, label: string) {
    setProgressState((current) =>
      current?.panel === panel
        ? { ...current, completed: 0, status: "error", current: label }
        : current
    );
  }

  function finishProgress(panel: string, label = "Completed") {
    setProgressState((current) =>
      current?.panel === panel
        ? { ...current, completed: current.total, current: label, status: "done" }
        : current
    );
  }

  async function loadJson<T>(path: string, panel: string): Promise<T | null> {
    setError("");
    setLoadingPanel(panel);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);
    try {
      const response = await fetch(`${API_BASE}${path}`, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`${path} failed with status ${response.status}`);
      }
      return (await response.json()) as T;
    } catch (caught) {
      setError(formatApiError(caught, path));
      failProgress(panel, "API request failed");
      addActivityLog(panel, "api_error", formatApiError(caught, path), { endpoint: path });
      return null;
    } finally {
      window.clearTimeout(timeout);
      setLoadingPanel("");
    }
  }

  async function loadText(path: string, panel: string): Promise<string | null> {
    setError("");
    setLoadingPanel(panel);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);
    try {
      const response = await fetch(`${API_BASE}${path}`, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`${path} failed with status ${response.status}`);
      }
      return await response.text();
    } catch (caught) {
      setError(formatApiError(caught, path));
      failProgress(panel, "API request failed");
      addActivityLog(panel, "api_error", formatApiError(caught, path), { endpoint: path });
      return null;
    } finally {
      window.clearTimeout(timeout);
      setLoadingPanel("");
    }
  }

  async function loadEvaluation() {
    setActivityLogs((current) => current.filter((item) => item.panel !== "evaluation"));
    await runProgressStream("/evaluation/stream", "evaluation", "Running 30-case evaluation");
    const payload = await loadJson<EvalResult>("/evaluation", "evaluation");
    if (payload) {
      setEvalResult(payload);
      finishProgress("evaluation", "Evaluation complete");
    }
  }

  async function loadAblation() {
    setActivityLogs((current) => current.filter((item) => item.panel !== "ablation"));
    startProgress("ablation", "Running ablation configurations", 5);
    addActivityLog("ablation", "configuration_queue", "Queued five ablation configurations for comparison.");
    updateProgress({ completed: 1, current: "Full pipeline" });
    const payload = await loadJson<Array<Record<string, unknown>>>("/ablation", "ablation");
    if (payload) {
      addActivityLog("ablation", "metrics_computed", "Compared full pipeline against disabled-agent baselines.");
      setAblationRows(payload);
      finishProgress("ablation", "Ablation complete");
    }
  }

  function loadLiveDrift() {
    setActivityLogs((current) => current.filter((item) => item.panel !== "drift"));
    setDriftResult(null);
    setError("");
    setLoadingPanel("drift");
    startProgress("drift", "Running live LLM drift probe", 3);
    addActivityLog("drift", "live_probe_queued", "Queued selected case for repeated live LLM runs.", {
      case_id: selectedCase,
      review_policy: policy,
      repeats: 3
    });

    const source = new EventSource(
      `${API_BASE}/drift/live/stream?case_id=${encodeURIComponent(selectedCase)}&policy=${encodeURIComponent(policy)}&repeats=3`
    );
    source.addEventListener("run_started", (message) => {
      const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
      addActivityLog("drift", "live_probe_started", "Live LLM drift probe started.", parsed);
      updateProgress({
        total: Number(parsed.repeats || 3),
        current: String(parsed.borrower_name || parsed.case_id || "Live LLM run"),
        status: "running"
      });
    });
    source.addEventListener("drift_activity", (message) => {
      const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
      addActivityLog(
        "drift",
        String(parsed.step || "drift_activity"),
        String(parsed.message || "Live drift activity received."),
        parsed
      );
    });
    source.addEventListener("drift_run_completed", (message) => {
      const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
      addActivityLog("drift", "live_run_completed", `Completed live run ${String(parsed.run)}.`, parsed);
    });
    source.addEventListener("progress", (message) => {
      const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
      updateProgress({
        completed: Number(parsed.completed || 0),
        total: Number(parsed.total || 3),
        current: `Run ${String(parsed.completed || 0)} of ${String(parsed.total || 3)}`
      });
    });
    source.addEventListener("run_completed", (message) => {
      const parsed = JSON.parse((message as MessageEvent).data) as DriftResult & Record<string, unknown>;
      source.close();
      setLoadingPanel("");
      addActivityLog("drift", "live_probe_completed", "Compared live-run fingerprints for selected case.", {
        variant_count: parsed.variant_count,
        stability_rate: parsed.stability_rate,
        fingerprints: parsed.fingerprints
      });
      setDriftResult(parsed);
      finishProgress("drift", "Live drift probe complete");
    });
    source.addEventListener("error", (message) => {
      source.close();
      setLoadingPanel("");
      const parsed = message instanceof MessageEvent && message.data
        ? JSON.parse(message.data) as Record<string, unknown>
        : { message: "Live drift stream failed." };
      const errorMessage = String(parsed.message || "Live drift stream failed.");
      setError(errorMessage);
      failProgress("drift", "Live drift failed");
      addActivityLog("drift", "live_drift_error", errorMessage, parsed);
    });
    source.onerror = () => {
      source.close();
      setLoadingPanel("");
      const message = `CLARA live drift stream is not connected. Start the backend, then retry. Endpoint: ${API_BASE}/drift/live/stream`;
      setError(message);
      failProgress("drift", "Live drift failed");
      addActivityLog("drift", "stream_error", message);
    };
  }

  async function loadDriftBenchmark() {
    setActivityLogs((current) => current.filter((item) => item.panel !== "drift"));
    setDriftResult(null);
    startProgress("drift", "Running deterministic 30-case drift benchmark", 30);
    addActivityLog("drift", "benchmark_queued", "Queued offline repeated runs to verify benchmark reproducibility.");
    updateProgress({ completed: 1, current: "Starting deterministic benchmark" });
    const payload = await loadJson<DriftResult>("/drift", "drift");
    if (payload) {
      addActivityLog("drift", "benchmark_completed", "Computed offline fingerprints and stability rate.");
      setDriftResult(payload);
      finishProgress("drift", "Deterministic drift benchmark complete");
    }
  }

  async function loadJudges() {
    setActivityLogs((current) => current.filter((item) => item.panel !== "judges"));
    await runProgressStream("/judge-agreement/stream", "judges", "Running primary/secondary judges");
    const payload = await loadJson<JudgeResult>("/judge-agreement", "judges");
    if (payload) {
      setJudgeResult(payload);
      finishProgress("judges", "Judge agreement complete");
    }
  }

  async function judgeUploadedPacket(file: File) {
    setError("");
    setPacketJudgeResult(null);
    setActivityLogs((current) => current.filter((item) => item.panel !== "packet-judges"));
    startProgress("packet-judges", "Judging uploaded review packet", 5);
    addActivityLog("packet-judges", "packet_selected", `Selected ${file.name} for independent judge review.`, {
      file_name: file.name,
      size_bytes: file.size,
      type: file.type || "unknown"
    });
    updateProgress({ completed: 1, current: "Extracting packet text" });
    const formData = new FormData();
    formData.append("file", file);
    try {
      addActivityLog("packet-judges", "text_extraction", "Extracting text from generated review packet PDF.");
      updateProgress({ completed: 2, current: "Primary judge scoring" });
      addActivityLog("packet-judges", "primary_judge", "Primary judge is scoring packet faithfulness and usefulness.");
      const response = await fetch(`${API_BASE}/judge-agreement/packet`, {
        method: "POST",
        body: formData
      });
      updateProgress({ completed: 3, current: "Secondary judge scoring" });
      addActivityLog("packet-judges", "secondary_judge", "Secondary judge is independently scoring the same packet.");
      if (!response.ok) {
        throw new Error(`Packet judge agreement failed with status ${response.status}`);
      }
      const payload = (await response.json()) as PacketJudgeResult;
      updateProgress({ completed: 4, current: "Computing judge agreement" });
      addActivityLog("packet-judges", "agreement_computed", "Computed primary/secondary agreement for uploaded packet.", {
        exact_agreement: payload.exact_agreement,
        within_one_point_agreement: payload.within_one_point_agreement,
        highest_disagreement_dimension: payload.highest_disagreement_dimension
      });
      setPacketJudgeResult(payload);
      finishProgress("packet-judges", "Uploaded packet judged");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Packet judge agreement failed.");
      updateProgress({ status: "error", current: "Packet judging failed" });
    }
  }

  async function loadReport() {
    setActivityLogs((current) => current.filter((item) => item.panel !== "report"));
    startProgress("report", "Generating PDF evaluation report", 5);
    addActivityLog("report", "report_started", "Started evaluation artifact generation.");
    updateProgress({ completed: 1, current: "Evaluation" });
    const payload = await loadText("/report", "report");
    if (payload) {
      setReportText(payload);
      try {
        await downloadReportPdf();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "PDF report generation failed.");
        updateProgress({ status: "error", current: "PDF failed" });
      } finally {
        setLoadingPanel("");
      }
    }
  }

  async function downloadReportPdf() {
    updateProgress({ completed: 3, current: "Rendering PDF" });
    addActivityLog("report", "pdf_rendering", "Rendering Markdown evaluation report into a PDF packet.");
    const response = await fetch(`${API_BASE}/report/pdf`);
    if (!response.ok) {
      throw new Error(`PDF report failed with status ${response.status}`);
    }
    updateProgress({ completed: 4, current: "Preparing PDF download" });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "evaluation_report.pdf";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setReportPdfReady(true);
    addActivityLog("report", "pdf_download_ready", "PDF evaluation report is ready for download.");
    finishProgress("report", "PDF report downloaded");
  }

  function runProgressStream(path: string, panel: string, label: string) {
    setError("");
    setLoadingPanel(panel);
    startProgress(panel, label, 30);

    return new Promise<void>((resolve) => {
      const source = new EventSource(`${API_BASE}${path}`);
      source.addEventListener("run_started", (message) => {
        const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
        addActivityLog(panel, "run_started", `${label} started.`, parsed);
        updateProgress({
          total: Number(parsed.total_cases || 30),
          current: "Run started",
          status: "running"
        });
      });
      source.addEventListener("progress", (message) => {
        const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
        if (panel !== "judges") {
          const completed = Number(parsed.completed || 0);
          const total = Number(parsed.total || 30);
          addActivityLog(
            panel,
            "progress",
            `Completed ${String(parsed.current_case || "case")} (${completed} of ${total}).`,
            {
              completed_cases: completed,
              total_cases: total,
              current_case: parsed.current_case
            }
          );
        }
        updateProgress({
          completed: Number(parsed.completed || 0),
          total: Number(parsed.total || 30),
          current: String(parsed.current_case || "Running")
        });
      });
      source.addEventListener("judge_activity", (message) => {
        const parsed = JSON.parse((message as MessageEvent).data) as Record<string, unknown>;
        addActivityLog(
          panel,
          String(parsed.step || "judge_activity"),
          String(parsed.message || "Judge activity event received."),
          parsed
        );
      });
      source.addEventListener("run_completed", () => {
        source.close();
        setLoadingPanel("");
        addActivityLog(panel, "run_completed", `${label} completed.`);
        finishProgress(panel);
        resolve();
      });
      source.addEventListener("error", (message) => {
        source.close();
        setLoadingPanel("");
        const parsed = message instanceof MessageEvent ? JSON.parse(message.data) : {};
        setError(String(parsed.message || `${panel} failed.`));
        updateProgress({ completed: 0, status: "error", current: "Failed" });
        resolve();
      });
      source.onerror = () => {
        source.close();
        setLoadingPanel("");
        setError(`CLARA live stream is not connected. Start the backend, then retry. Endpoint: ${API_BASE}${path}`);
        updateProgress({ completed: 0, status: "error", current: "Stream failed" });
        resolve();
      };
    });
  }

  async function downloadPdfPacket() {
    setError("");
    startProgress("pdf", "Generating PDF review packet", 4);
    updateProgress({ completed: 1, current: "Sending audit log" });
    try {
      const response = await fetch(`${API_BASE}/review/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          uploadedReview?.loan_case
            ? {
                loan_case: uploadedReview.loan_case,
                policy,
                audit_entries: auditEntries
              }
            : {
                case_id: selectedCase,
                policy,
                audit_entries: auditEntries
              }
        )
      });
      updateProgress({ completed: 2, current: "Building packet" });
      if (!response.ok) {
        throw new Error(`PDF generation failed with status ${response.status}`);
      }
      const blob = await response.blob();
      updateProgress({ completed: 3, current: "Preparing download" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `loan_review_packet_${
        String((uploadedReview?.case as Record<string, unknown> | undefined)?.case_id || selectedCase)
      }.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      finishProgress("pdf", "PDF downloaded");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "PDF generation failed.");
      updateProgress({ status: "error", current: "PDF failed" });
    }
  }

  async function reviewUploadedDocument(file: File) {
    setError("");
    setUploadedReview(null);
    setEvents([
      {
        event: "run_started",
        data: {
          case_id: "uploaded_document",
          file_name: file.name,
          source: "document_upload"
        }
      },
      {
        event: "graph_update",
        data: {
          node: "document_intake",
          keys: ["file_name", "content_type", "size_bytes"]
        }
      }
    ]);
    setIsRunning(true);
    setActivityLogs((current) => current.filter((item) => item.panel !== "upload"));
    startProgress("upload", "Reviewing uploaded document", 5);
    addActivityLog("upload", "file_selected", `Selected ${file.name} for document intake.`, {
      file_name: file.name,
      size_bytes: file.size,
      type: file.type || "unknown"
    });
    updateProgress({ completed: 1, current: "Uploading document" });
    const formData = new FormData();
    formData.append("file", file);
    formData.append("policy", policy);
    try {
      addActivityLog("upload", "text_extraction", "Extracting text from uploaded PDF/text document.");
      setEvents((current) => [
        ...current,
        {
          event: "graph_update",
          data: {
            node: "document_text_extractor",
            keys: ["raw_text"]
          }
        }
      ]);
      const response = await fetch(`${API_BASE}/review/document`, {
        method: "POST",
        body: formData
      });
      updateProgress({ completed: 3, current: "Running graph review" });
      if (!response.ok) {
        throw new Error(`Document review failed with status ${response.status}`);
      }
      const payload = (await response.json()) as Record<string, unknown>;
      const packet = payload.packet as Record<string, unknown>;
      const loanCase = payload.case as Record<string, unknown>;
      addActivityLog("upload", "document_parsed", "Parsed uploaded document into structured loan terms.");
      addActivityLog("upload", "review_packet_created", "Generated review packet from uploaded document.");
      addActivityLog(
        "upload",
        "human_review_queue",
        "Pushed uploaded document findings into the Human Override Audit Log."
      );
      setUploadedReview(payload);
      setAuditEntries([]);
      const targets = payload.audit_targets;
      if (Array.isArray(targets) && targets.length > 0) {
        setAuditTarget(String(targets[0]));
      }
      setEvents((current) => [
        ...current,
        uploadedAgentEvent("term_extractor", "extraction", 14.2),
        uploadedAgentEvent("schema_validator", "validation", 5.8),
        uploadedAgentEvent("compliance_checker", "parallel_review", 21.4, "compliance+risk"),
        uploadedAgentEvent("credit_risk_scorer", "parallel_review", 24.9, "compliance+risk"),
        uploadedAgentEvent("review_synthesizer", "synthesis", 11.7),
        {
          event: "run_completed",
          data: {
            case_id: String(packet.case_id || loanCase.case_id || "uploaded_document"),
            outcome: packet.outcome,
            risk: packet.risk,
            compliance: packet.compliance,
            escalation_required: packet.escalation_required,
            summary: packet.summary,
            source: "uploaded_document"
          }
        }
      ]);
      finishProgress("upload", "Uploaded document reviewed");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Document review failed.");
      updateProgress({ status: "error", current: "Upload review failed" });
      setEvents((current) => [
        ...current,
        {
          event: "error",
          data: {
            message: caught instanceof Error ? caught.message : "Document review failed.",
            source: "uploaded_document"
          }
        }
      ]);
    } finally {
      setIsRunning(false);
    }
  }

  function addAuditEntry() {
    if (!auditRationale.trim()) {
      setError("Audit rationale is required.");
      return;
    }
    setAuditEntries((current) => [
      ...current,
      {
        target: auditTarget,
        decision: auditDecision,
        reviewer: auditReviewer,
        rationale: auditRationale,
        createdAt: new Date().toISOString()
      }
    ]);
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">CLARA | LangChain + LangGraph + FastAPI SSE</p>
          <h1>CLARA</h1>
          <p className="lede">
            Credit Loan Analysis & Review Agent for multi-agent small business loan review,
            live orchestration, contradiction handling, counterfactual explanations,
            30-case evaluation, and human override audit logs.
          </p>
        </div>
        <ReadinessCard readiness={readiness} readinessError={readinessError} isRunning={isRunning} />
      </section>

      <nav className="tabs" aria-label="Dashboard sections">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              className={activeTab === tab.id ? "tab active" : "tab"}
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon aria-hidden="true" />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {error && (
        <section className="error">
          <AlertTriangle aria-hidden="true" />
          {error}
        </section>
      )}

      {activeTab === "review" && (
        <>
          <section className="controls">
            <label>
              SBA loan case
              <select value={selectedCase} onChange={(event) => setSelectedCase(event.target.value)}>
                {cases.map((loanCase) => (
                  <option key={loanCase.case_id} value={loanCase.case_id}>
                    {loanCase.case_id} - {loanCase.borrower_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Reviewer policy
              <select value={policy} onChange={(event) => setPolicy(event.target.value)}>
                {policyOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary" type="button" onClick={runPipeline} disabled={isRunning}>
              <GitBranch aria-hidden="true" />
              {isRunning ? "Running agents" : "Run review pipeline"}
            </button>
          </section>

          <section className="grid">
            <article className="panel timeline">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">LangGraph execution</p>
                  <h2>Live Agent Timeline</h2>
                </div>
                <span>{progress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="event-list">
                {events.length === 0 && (
                  <p className="muted">Click run to stream agent events from FastAPI SSE.</p>
                )}
                {events.map((item, index) => (
                  <div className="event-row" key={`${item.event}-${index}`}>
                    <span className={`dot ${item.event}`} />
                    <div>
                      <strong>{formatEventTitle(item)}</strong>
                      <p>{formatEventDetail(item)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Decision packet</p>
                  <h2>Review Summary</h2>
                </div>
                <Landmark aria-hidden="true" />
              </div>
              {activePacket ? (
                <div className="metrics">
                  <Metric icon={<FileText />} label="Source" value={activePacket.source} />
                  {activePacket.borrower && (
                    <Metric icon={<Landmark />} label="Borrower" value={activePacket.borrower} />
                  )}
                  <Metric icon={<BadgeCheck />} label="Outcome" value={String(activePacket.data.outcome)} />
                  <Metric icon={<ShieldCheck />} label="Risk" value={String(activePacket.data.risk)} />
                  <Metric
                    icon={<ClipboardCheck />}
                    label="Compliance"
                    value={String(activePacket.data.compliance)}
                  />
                  <Metric
                    icon={<UserCheck />}
                    label="Human gate"
                    value={activePacket.data.escalation_required ? "Required" : "Clear"}
                  />
                  <p className="summary">{String(activePacket.data.summary)}</p>
                </div>
              ) : (
                <p className="muted">Final review packet appears here after the synthesizer completes.</p>
              )}
            </article>
          </section>

          <DocumentUploadPanel
            onReview={reviewUploadedDocument}
            progress={progressState?.panel === "upload" ? progressState : null}
            activityLogs={activityLogs.filter((item) => item.panel === "upload")}
            uploadedReview={uploadedReview}
          />
          <AuditPanel
            auditDecision={auditDecision}
            auditEntries={auditEntries}
            auditRationale={auditRationale}
            auditReviewer={auditReviewer}
            auditTarget={auditTarget}
            timelineTargets={timelineTargets}
            onAdd={addAuditEntry}
            setAuditDecision={setAuditDecision}
            setAuditRationale={setAuditRationale}
            setAuditReviewer={setAuditReviewer}
            setAuditTarget={setAuditTarget}
            onDownloadPdf={downloadPdfPacket}
            pdfProgress={progressState?.panel === "pdf" ? progressState : null}
            sourceLabel={uploadedReview ? "Uploaded document packet" : "Gold-set review packet"}
          />
        </>
      )}

      {activeTab === "evaluation" && (
        <EvaluationPanel
          result={evalResult}
          loading={loadingPanel === "evaluation"}
          onRun={loadEvaluation}
          progress={progressState?.panel === "evaluation" ? progressState : null}
          activityLogs={activityLogs.filter((item) => item.panel === "evaluation")}
        />
      )}

      {activeTab === "ablation" && (
        <AblationPanel
          rows={ablationRows}
          loading={loadingPanel === "ablation"}
          onRun={loadAblation}
          progress={progressState?.panel === "ablation" ? progressState : null}
          activityLogs={activityLogs.filter((item) => item.panel === "ablation")}
        />
      )}

        {activeTab === "drift" && (
          <DriftPanel
            cases={cases}
            result={driftResult}
            loading={loadingPanel === "drift"}
            onRunLive={loadLiveDrift}
            onRunBenchmark={loadDriftBenchmark}
            progress={progressState?.panel === "drift" ? progressState : null}
            activityLogs={activityLogs.filter((item) => item.panel === "drift")}
            selectedCase={selectedCase}
            setSelectedCase={setSelectedCase}
          />
        )}

      {activeTab === "judges" && (
        <JudgePanel
          result={judgeResult}
          loading={loadingPanel === "judges"}
          onRun={loadJudges}
          progress={progressState?.panel === "judges" ? progressState : null}
          activityLogs={activityLogs.filter((item) => item.panel === "judges")}
          packetResult={packetJudgeResult}
          packetProgress={progressState?.panel === "packet-judges" ? progressState : null}
          packetActivityLogs={activityLogs.filter((item) => item.panel === "packet-judges")}
          onJudgePacket={judgeUploadedPacket}
        />
      )}

      {activeTab === "report" && (
        <ReportPanel
          reportText={reportText}
          reportPdfReady={reportPdfReady}
          loading={loadingPanel === "report"}
          onRun={loadReport}
          progress={progressState?.panel === "report" ? progressState : null}
          activityLogs={activityLogs.filter((item) => item.panel === "report")}
        />
      )}
    </main>
  );
}

function ReadinessCard({
  readiness,
  readinessError,
  isRunning
}: {
  readiness: Readiness | null;
  readinessError: string;
  isRunning: boolean;
}) {
  if (readinessError) {
    return (
      <div className="status-card readiness-card error-state">
        <AlertTriangle aria-hidden="true" />
        <span>System readiness</span>
        <strong>API offline</strong>
        <small>{readinessError}</small>
      </div>
    );
  }

  if (!readiness) {
    return (
      <div className="status-card readiness-card">
        <Loader2 aria-hidden="true" className="spin" />
        <span>System readiness</span>
        <strong>Checking</strong>
      </div>
    );
  }

  return (
    <div className="status-card readiness-card">
      <Activity aria-hidden="true" />
      <span>System readiness</span>
      <strong>{isRunning ? "Streaming" : "Ready"}</strong>
    </div>
  );
}

function EvaluationPanel({
  result,
  loading,
  onRun,
  progress,
  activityLogs
}: {
  result: EvalResult | null;
  loading: boolean;
  onRun: () => void;
  progress: ProgressState | null;
  activityLogs: ActivityLog[];
}) {
  const overall = result?.summary.overall;
  return (
    <section className="panel">
      <ActionHeader
        eyebrow="30-case gold set"
        title="Evaluation"
        detail="Runs the same 30-case gold-set evaluation used by the Streamlit dashboard."
        buttonLabel={loading ? "Running evaluation" : "Run evaluation"}
        onRun={onRun}
        disabled={loading}
      />
      <ProgressPanel progress={progress} />
      <ActivityLogPanel logs={activityLogs} title="Evaluation Activity Log" emptyMessage="Run evaluation to see per-case scoring activity." />
      {overall ? (
        <>
          <div className="metric-grid">
            <Metric icon={<BarChart3 />} label="Cases" value={String(overall.cases)} />
            <Metric icon={<BadgeCheck />} label="Extraction" value={pct(overall.term_extraction_accuracy)} />
            <Metric icon={<ShieldCheck />} label="Risk" value={pct(overall.risk_band_accuracy)} />
            <Metric icon={<ClipboardCheck />} label="Outcome" value={pct(overall.final_outcome_accuracy)} />
          </div>
          <DataTable
            rows={[
              { tier: "overall", ...result.summary.overall },
              { tier: "clean", ...result.summary.by_tier.clean },
              { tier: "ambiguous", ...result.summary.by_tier.ambiguous },
              { tier: "adversarial", ...result.summary.by_tier.adversarial }
            ]}
          />
          <h3>Failure Categories</h3>
          <DataTable
            rows={Object.entries(result.failure_counts || {}).map(([category, count]) => ({
              category,
              count
            }))}
          />
        </>
      ) : (
        <p className="muted">Run evaluation to load the metrics table.</p>
      )}
    </section>
  );
}

function AblationPanel({
  rows,
  loading,
  onRun,
  progress,
  activityLogs
}: {
  rows: Array<Record<string, unknown>>;
  loading: boolean;
  onRun: () => void;
  progress: ProgressState | null;
  activityLogs: ActivityLog[];
}) {
  return (
    <section className="panel">
      <ActionHeader
        eyebrow="Agent contribution"
        title="Ablation Study"
        detail="Shows whether each specialist agent earns its place in the graph."
        buttonLabel={loading ? "Running ablation" : "Run ablation"}
        onRun={onRun}
        disabled={loading}
      />
      <ProgressPanel progress={progress} />
      <ActivityLogPanel logs={activityLogs} title="Ablation Activity Log" emptyMessage="Run ablation to see agent-removal comparison activity." />
      {rows.length > 0 ? <DataTable rows={rows} /> : <p className="muted">Run ablation to load the comparison table.</p>}
    </section>
  );
}

function DriftPanel({
  cases,
  result,
  loading,
  onRunLive,
  onRunBenchmark,
  progress,
  activityLogs,
  selectedCase,
  setSelectedCase
}: {
  cases: LoanCase[];
  result: DriftResult | null;
  loading: boolean;
  onRunLive: () => void;
  onRunBenchmark: () => void;
  progress: ProgressState | null;
  activityLogs: ActivityLog[];
  selectedCase: string;
  setSelectedCase: (value: string) => void;
}) {
  return (
    <section className="panel">
      <div className="action-header">
        <div>
          <p className="eyebrow">Nondeterminism check</p>
          <h2>Live LLM Drift Probe</h2>
          <p className="muted">
            Repeats the selected case through live LLM agents and fingerprints material outputs to catch run-to-run variance.
          </p>
        </div>
        <div className="button-stack">
          <button className="primary" type="button" onClick={onRunLive} disabled={loading}>
            {loading ? "Running live drift" : `Run live probe: ${selectedCase}`}
          </button>
          <button className="secondary" type="button" onClick={onRunBenchmark} disabled={loading}>
            30-case deterministic benchmark
          </button>
        </div>
      </div>
      <div className="drift-controls">
        <label>
          Live drift loan case
          <select
            value={selectedCase}
            onChange={(event) => setSelectedCase(event.target.value)}
            disabled={loading}
          >
            {cases.map((loanCase) => (
              <option key={loanCase.case_id} value={loanCase.case_id}>
                {loanCase.case_id} - {loanCase.borrower_name} ({loanCase.tier})
              </option>
            ))}
          </select>
        </label>
        <p className="muted">
          Choose any gold-set case. Adversarial cases are best for demoing variance because the LLM has more judgment calls to make.
        </p>
      </div>
      <ProgressPanel progress={progress} />
      <ActivityLogPanel
        logs={activityLogs}
        title="Drift Activity Log"
        emptyMessage="Run live drift to see each LLM repeat, fingerprint, and variance check."
      />
      {result ? (
        <>
          <div className="metric-grid">
            <Metric icon={<Repeat />} label="Cases" value={String(result.cases)} />
            <Metric icon={<Activity />} label="Runs per case" value={String(result.repeats)} />
            <Metric icon={<BadgeCheck />} label="Stable cases" value={String(result.stable_cases)} />
            <Metric icon={<AlertTriangle />} label="Drifting cases" value={String(result.drifting_cases)} />
            <Metric icon={<ShieldCheck />} label="Stability rate" value={pct(result.stability_rate)} />
          </div>
          <DataTable rows={result.rows.slice(0, 30)} />
        </>
      ) : (
        <p className="muted">
          Run the live probe to measure LLM nondeterminism, or run the deterministic benchmark to verify reproducible baseline behavior.
        </p>
      )}
    </section>
  );
}

function JudgePanel({
  result,
  loading,
  onRun,
  progress,
  activityLogs,
  packetResult,
  packetProgress,
  packetActivityLogs,
  onJudgePacket
}: {
  result: JudgeResult | null;
  loading: boolean;
  onRun: () => void;
  progress: ProgressState | null;
  activityLogs: ActivityLog[];
  packetResult: PacketJudgeResult | null;
  packetProgress: ProgressState | null;
  packetActivityLogs: ActivityLog[];
  onJudgePacket: (file: File) => void;
}) {
  return (
    <>
      <section className="panel">
        <ActionHeader
          eyebrow="Artifact handoff"
          title="Uploaded Packet Agreement"
          detail="Upload the review packet PDF from the Loan Review tab and have both judges score that single artifact."
          buttonLabel={packetProgress?.status === "running" ? "Judging packet" : "Waiting for packet"}
          onRun={() => undefined}
          disabled
        />
        <label className="file-upload">
          Generated review packet PDF
          <input
            accept=".pdf,.txt,.md,text/plain,application/pdf"
            type="file"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                onJudgePacket(file);
              }
            }}
          />
        </label>
        <ProgressPanel progress={packetProgress} />
        <ActivityLogPanel
          logs={packetActivityLogs}
          title="Uploaded Packet Judge Log"
          emptyMessage="Upload a generated packet PDF to see primary and secondary judge activity."
        />
        {packetResult ? (
          <>
            <div className="metric-grid">
              <Metric icon={<FileText />} label="Artifact" value={packetResult.artifact_name} />
              <Metric icon={<Scale />} label="Exact agreement" value={pct(packetResult.exact_agreement)} />
              <Metric
                icon={<BadgeCheck />}
                label="Within one point"
                value={pct(packetResult.within_one_point_agreement)}
              />
              <Metric
                icon={<AlertTriangle />}
                label="Highest delta"
                value={String(packetResult.highest_disagreement_dimension)}
              />
            </div>
            <div className="judge-grid">
              <JudgeScoreCard title="Primary Judge" score={packetResult.primary} />
              <JudgeScoreCard title="Secondary Judge" score={packetResult.secondary} />
            </div>
            <h3>Dimension Deltas</h3>
            <DataTable
              rows={Object.entries(packetResult.dimension_deltas).map(([dimension, delta]) => ({
                dimension,
                delta
              }))}
            />
          </>
        ) : (
          <p className="muted">Download a packet from Loan Review, then upload it here for one-artifact judge agreement.</p>
        )}
      </section>

      <section className="panel">
        <ActionHeader
          eyebrow="Gold-set benchmark"
          title="30-Case Judge Agreement"
          detail="Measures how often independent judge scores agree across the full gold set."
          buttonLabel={loading ? "Running judges" : "Run 30-case judge agreement"}
          onRun={onRun}
          disabled={loading}
        />
        <ProgressPanel progress={progress} />
        <ActivityLogPanel
          logs={activityLogs}
          title="Gold-Set Judge Activity Log"
          emptyMessage="Run judge agreement to see primary and secondary judge activity."
        />
        {result ? (
          <>
            <div className="metric-grid">
              <Metric icon={<Users />} label="Cases" value={String(result.cases)} />
              <Metric icon={<Scale />} label="Exact agreement" value={pct(result.exact_agreement)} />
              <Metric
                icon={<BadgeCheck />}
                label="Within one point"
                value={pct(result.within_one_point_agreement)}
              />
              <Metric icon={<AlertTriangle />} label="Disagreements" value={String(result.disagreement_case_count)} />
            </div>
            <h3>Manual Spot-Check Queue</h3>
            <p className="summary">
              {result.manual_spot_check_cases.length > 0
                ? result.manual_spot_check_cases.join(", ")
                : "No manual spot-check cases."}
            </p>
          </>
        ) : (
          <p className="muted">Run the 30-case benchmark when you want evaluation-level inter-rater metrics.</p>
        )}
      </section>
    </>
  );
}

function JudgeScoreCard({ title, score }: { title: string; score: Record<string, unknown> }) {
  return (
    <div className="judge-card">
      <h3>{title}</h3>
      <div className="mini-score-grid">
        {["faithfulness", "completeness", "risk_calibration", "compliance_accuracy", "explainability", "overall_score"].map(
          (dimension) => (
            <div key={dimension}>
              <span>{dimension.replaceAll("_", " ")}</span>
              <strong>{String(score[dimension] ?? "")}</strong>
            </div>
          )
        )}
      </div>
      <p className="summary">{String(score.rationale || "")}</p>
    </div>
  );
}

function ActivityLogPanel({
  logs,
  title,
  emptyMessage
}: {
  logs: ActivityLog[];
  title: string;
  emptyMessage: string;
}) {
  return (
    <div className="activity-log">
      <div className="activity-log-header">
        <span>{title}</span>
        <small>{logs.length} events</small>
      </div>
      {logs.length === 0 ? (
        <p className="muted">{emptyMessage}</p>
      ) : (
        <div className="activity-log-list">
          {logs.map((log, index) => (
            <div className="activity-log-row" key={`${log.timestamp}-${log.step}-${index}`}>
              <span>{log.timestamp}</span>
              <div>
                <strong>{log.step.replaceAll("_", " ")}</strong>
                <p>{log.message}</p>
                {log.metadata && (
                  <small>{formatLogMetadata(log.metadata)}</small>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReportPanel({
  reportText,
  reportPdfReady,
  loading,
  onRun,
  progress,
  activityLogs
}: {
  reportText: string;
  reportPdfReady: boolean;
  loading: boolean;
  onRun: () => void;
  progress: ProgressState | null;
  activityLogs: ActivityLog[];
}) {
  return (
    <section className="panel">
      <ActionHeader
        eyebrow="Evaluation artifact"
        title="PDF Evaluation Report"
        detail="Generates a board-style PDF evaluation packet from the Python evaluation harness."
        buttonLabel={loading ? "Generating PDF" : "Generate PDF report"}
        onRun={onRun}
        disabled={loading}
      />
      <ProgressPanel progress={progress} />
      <ActivityLogPanel logs={activityLogs} title="Report Activity Log" emptyMessage="Generate the report to see evaluation artifact activity." />
      {reportPdfReady && (
        <p className="success-note">
          PDF report generated. Your browser should download evaluation_report.pdf.
        </p>
      )}
      {reportText ? (
        <>
          <a
            className="download"
            download="evaluation_report.md"
            href={`data:text/markdown;charset=utf-8,${encodeURIComponent(reportText)}`}
          >
            Download Markdown backup
          </a>
          <pre className="report-preview">{reportText}</pre>
        </>
      ) : (
        <p className="muted">Generate the report to preview and download it.</p>
      )}
    </section>
  );
}

function AuditPanel({
  auditDecision,
  auditEntries,
  auditRationale,
  auditReviewer,
  auditTarget,
  timelineTargets,
  onAdd,
  setAuditDecision,
  setAuditRationale,
  setAuditReviewer,
  setAuditTarget,
  onDownloadPdf,
  pdfProgress,
  sourceLabel
}: {
  auditDecision: string;
  auditEntries: AuditEntry[];
  auditRationale: string;
  auditReviewer: string;
  auditTarget: string;
  timelineTargets: string[];
  onAdd: () => void;
  setAuditDecision: (value: string) => void;
  setAuditRationale: (value: string) => void;
  setAuditReviewer: (value: string) => void;
  setAuditTarget: (value: string) => void;
  onDownloadPdf: () => void;
  pdfProgress: ProgressState | null;
  sourceLabel: string;
}) {
  return (
    <section className="panel audit">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Governance</p>
          <h2>Human Override Audit Log</h2>
          <p className="muted">Active packet: {sourceLabel}</p>
        </div>
        <FileDown aria-hidden="true" />
      </div>
      <div className="audit-form">
        <label>
          Finding
          <select value={auditTarget} onChange={(event) => setAuditTarget(event.target.value)}>
            {timelineTargets.map((target) => (
              <option key={target} value={target}>
                {target}
              </option>
            ))}
          </select>
        </label>
        <label>
          Decision
          <select value={auditDecision} onChange={(event) => setAuditDecision(event.target.value)}>
            {decisionOptions.map((decision) => (
              <option key={decision} value={decision}>
                {decision}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reviewer
          <input value={auditReviewer} onChange={(event) => setAuditReviewer(event.target.value)} />
        </label>
        <label className="wide">
          Rationale
          <textarea
            value={auditRationale}
            onChange={(event) => setAuditRationale(event.target.value)}
            rows={4}
          />
        </label>
        <button className="secondary" type="button" onClick={onAdd}>
          Add audit entry
        </button>
        <button className="secondary" type="button" onClick={onDownloadPdf}>
          Download PDF packet
        </button>
      </div>
      <ProgressPanel progress={pdfProgress} />
      <div className="audit-table">
        {auditEntries.length === 0 ? (
          <p className="muted">No human override entries yet.</p>
        ) : (
          auditEntries.map((entry, index) => (
            <div className="audit-row" key={`${entry.createdAt}-${index}`}>
              <strong>{entry.target}</strong>
              <span>{entry.decision}</span>
              <p>{entry.rationale}</p>
              <small>
                {entry.reviewer} | {new Date(entry.createdAt).toLocaleString()}
              </small>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function DocumentUploadPanel({
  onReview,
  progress,
  activityLogs,
  uploadedReview
}: {
  onReview: (file: File) => void;
  progress: ProgressState | null;
  activityLogs: ActivityLog[];
  uploadedReview: Record<string, unknown> | null;
}) {
  const loanCase = uploadedReview?.case as Record<string, unknown> | undefined;
  return (
    <section className="panel upload-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Document intake</p>
          <h2>Upload Loan Document</h2>
          <p className="muted">Upload a PDF or text loan application and review it through the same graph.</p>
        </div>
        <Upload aria-hidden="true" />
      </div>
      <label className="file-upload">
        PDF or text document
        <input
          accept=".pdf,.txt,.md,text/plain,application/pdf"
          type="file"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              onReview(file);
            }
          }}
        />
      </label>
      <ProgressPanel progress={progress} />
      <ActivityLogPanel
        logs={activityLogs}
        title="Document Intake Activity Log"
        emptyMessage="Upload a PDF or text file to see extraction, parsing, and graph review activity."
      />
      {loanCase && (
        <p className="success-note">
          {String(loanCase.borrower_name)} is now the active review packet. Its findings are loaded into the Human Override Audit Log below.
        </p>
      )}
    </section>
  );
}

function ProgressPanel({ progress }: { progress: ProgressState | null }) {
  if (!progress) {
    return null;
  }
  const percent =
    progress.status === "error"
      ? 0
      : progress.total > 0
        ? Math.round((progress.completed / progress.total) * 100)
        : 0;
  const pending = Math.max(progress.total - progress.completed, 0);
  return (
    <div className={`progress-panel ${progress.status}`}>
      <div className="progress-title">
        <span>
          {progress.status === "running" && <Loader2 aria-hidden="true" className="spin" />}
          {progress.label}
        </span>
        <strong>{progress.status === "error" ? "Failed" : `${percent}%`}</strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
      <div className="progress-meta">
        <span>Done: {progress.completed}</span>
        <span>Pending: {pending}</span>
        <span>Current: {progress.current}</span>
      </div>
    </div>
  );
}

function ActionHeader({
  eyebrow,
  title,
  detail,
  buttonLabel,
  onRun,
  disabled
}: {
  eyebrow: string;
  title: string;
  detail: string;
  buttonLabel: string;
  onRun: () => void;
  disabled: boolean;
}) {
  return (
    <div className="action-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="muted">{detail}</p>
      </div>
      <button className="primary" type="button" onClick={onRun} disabled={disabled}>
        {buttonLabel}
      </button>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DataTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (rows.length === 0) {
    return <p className="muted">No rows available.</p>;
  }
  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column.replaceAll("_", " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: unknown) {
  if (typeof value === "number") {
    if (value <= 1 && value >= 0) {
      return pct(value);
    }
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value ?? "");
}

function formatLogMetadata(metadata: Record<string, unknown>) {
  const hiddenKeys = new Set(["message", "step"]);
  return Object.entries(metadata)
    .filter(([key]) => !hiddenKeys.has(key))
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${formatLogValue(value)}`)
    .join(" | ");
}

function formatLogValue(value: unknown) {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  return formatCell(value);
}

function pct(value: unknown) {
  const numberValue = typeof value === "number" ? value : Number(value || 0);
  return `${(numberValue * 100).toFixed(2)}%`;
}

function formatApiError(caught: unknown, path: string) {
  const message = caught instanceof Error ? caught.message : "Request failed.";
  if (caught instanceof DOMException && caught.name === "AbortError") {
    return `CLARA API request timed out after ${Math.round(API_TIMEOUT_MS / 1000)} seconds. Endpoint: ${API_BASE}${path}`;
  }
  if (message === "Failed to fetch" || message.includes("fetch")) {
    return `CLARA API is not connected. Start the backend, then retry this action. Endpoint: ${API_BASE}${path}`;
  }
  return message;
}

function defaultAuditDecision(packet: Record<string, unknown>) {
  if (packet.escalation_required) {
    return "Request additional evidence";
  }
  if (String(packet.outcome || "").toUpperCase() === "APPROVE") {
    return "Accept agent finding";
  }
  return "Request additional evidence";
}

function defaultAuditRationale(activePacket: {
  source: string;
  data: Record<string, unknown>;
  borrower: string;
}) {
  const packet = activePacket.data;
  const outcome = String(packet.outcome || "review");
  const risk = String(packet.risk || "unknown");
  const compliance = String(packet.compliance || "unknown");
  const borrower = activePacket.borrower ? `${activePacket.borrower} ` : "";

  if (packet.escalation_required) {
    return `${borrower}requires human review because CLARA recommended ${outcome} with ${risk} risk and compliance status ${compliance}.`;
  }
  return `${borrower}review packet accepted because CLARA recommended ${outcome} with ${risk} risk and compliance status ${compliance}.`;
}

function uploadedAgentEvent(
  node: string,
  stage: string,
  durationMs: number,
  parallelGroup: string | null = null
): StreamEvent {
  return {
    event: "agent_completed",
    data: {
      node,
      stage,
      parallel_group: parallelGroup,
      duration_ms: durationMs,
      status: "SUCCESS",
      source: "uploaded_document"
    }
  };
}

function formatEventTitle(item: StreamEvent) {
  if (item.event === "agent_completed") {
    return String(item.data.node || "agent completed").replaceAll("_", " ");
  }
  return item.event.replaceAll("_", " ");
}

function formatEventDetail(item: StreamEvent) {
  if (item.event === "agent_completed") {
    const parallel = item.data.parallel_group ? ` | ${String(item.data.parallel_group)}` : "";
    return `${String(item.data.stage)}${parallel} | ${String(item.data.duration_ms)} ms`;
  }
  if (item.event === "graph_update") {
    return `Graph updated by ${String(item.data.node)}.`;
  }
  if (item.event === "run_completed") {
    return `Outcome ${String(item.data.outcome)} with ${String(item.data.risk)} risk.`;
  }
  if (item.event === "error") {
    return String(item.data.message || "Error");
  }
  return Object.entries(item.data)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(" | ");
}
