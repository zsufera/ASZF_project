import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Case, HistoryItem } from "../lib/types";

export interface CaseHistoryState {
  items: HistoryItem[];
  is_repeated: boolean;
}

export function useCaseData(caseId?: string) {
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [history, setHistory] = useState<CaseHistoryState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refetch = useCallback(() => {
    if (!caseId) return;
    setLoading(true);
    api
      .getCase(caseId)
      .then((currentCase) => {
        setCaseData(currentCase);
        setError("");
        api
          .getHistory(currentCase.sender_email_masked, currentCase.sender_email_key)
          .then(setHistory)
          .catch(() => {});
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Hiba az ugy betoltese soran"))
      .finally(() => setLoading(false));
  }, [caseId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { caseData, history, loading, error, refetch, setCaseData };
}
