import { useCallback, useState } from "react";
import { api } from "../lib/api";
import type { Case, FeedbackReason, OutputMode, TimelineStep, User } from "../lib/types";

interface UseCaseActionsParams {
  caseData: Case | null;
  user: User | null;
  outputMode: OutputMode;
  onRefresh: () => void;
  onApproved: (result: { subject_unmasked: string; body_unmasked: string }) => void;
  show: (message: string, type?: "success" | "error" | "info") => void;
}

export function useCaseActions({
  caseData,
  user,
  outputMode,
  onRefresh,
  onApproved,
  show,
}: UseCaseActionsParams) {
  const [processing, setProcessing] = useState(false);
  const [processingSteps, setProcessingSteps] = useState<TimelineStep[]>([]);
  const [escalating, setEscalating] = useState(false);

  const handleProcess = useCallback(async () => {
    if (!caseData || !user) return;
    setProcessing(true);
    setProcessingSteps([]);
    try {
      await api.streamCaseProcess(
        { case_id: caseData.case_id, output_mode: outputMode, username: user.username },
        (event) => {
          if (event.event === "step") {
            const step = event.data.step as TimelineStep | undefined;
            if (step) setProcessingSteps((prev) => [...prev, step]);
          }
          if (event.event === "error") {
            throw new Error(String(event.data.error ?? "Hiba a feldolgozás során"));
          }
        },
      );
      onRefresh();
    } catch (err) {
      show(err instanceof Error ? err.message : "Hiba a feldolgozás során", "error");
    } finally {
      setProcessing(false);
    }
  }, [caseData, onRefresh, outputMode, show, user]);

  const handleSave = useCallback(
    async (subject: string, body: string) => {
      if (!caseData || !user) return;
      await api.saveDraft({
        case_id: caseData.case_id,
        subject,
        body_masked: body,
        output_mode: outputMode,
        citations: caseData.agent_state.draft?.citations ?? [],
        username: user.username,
      });
      show("Vázlat mentve");
      onRefresh();
    },
    [caseData, onRefresh, outputMode, show, user],
  );

  const handleApprove = useCallback(
    async (subject: string, body: string, versionId: string) => {
      if (!caseData || !user) return;
      const result = await api.approveCase({
        case_id: caseData.case_id,
        subject_masked: subject,
        body_masked: body,
        username: user.username,
        role: user.role,
        draft_version_id: versionId,
      });
      onApproved(result);
    },
    [caseData, onApproved, user],
  );

  const handleFeedback = useCallback(
    async (rating: "jo" | "rossz", reason?: FeedbackReason) => {
      if (!caseData || !user) return;
      await api.sendFeedback({
        case_id: caseData.case_id,
        rating,
        reason,
        wrong_source: reason === "rossz_forras",
        username: user.username,
      });
      show(rating === "jo" ? "Köszönjük a visszajelzést!" : "Visszajelzés elküldve");
    },
    [caseData, show, user],
  );

  const handleEscalateToSupervisor = useCallback(async () => {
    if (!caseData || !user || caseData.status === "eszkalalva") return;
    setEscalating(true);
    try {
      await api.updateStatus({
        case_id: caseData.case_id,
        target_status: "eszkalalva",
        username: user.username,
        role: user.role,
      });
      show("Ügy supervisor sorba küldve", "success");
      onRefresh();
    } catch (err) {
      show(err instanceof Error ? err.message : "Eszkalációs átadás hiba", "error");
    } finally {
      setEscalating(false);
    }
  }, [caseData, onRefresh, show, user]);

  return { processing, processingSteps, escalating, handleProcess, handleSave, handleApprove, handleFeedback, handleEscalateToSupervisor };
}
