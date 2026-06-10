import type { FeedbackReason } from "./types";

export const FEEDBACK_REASON_LABELS: Record<FeedbackReason, string> = {
  pontatlan: "Pontatlan tartalom",
  hianyos: "Hianyos valasz",
  rossz_hangnem: "Nem megfelelo hangnem",
  rossz_forras: "Rossz forras",
  felesleges_eszkalacio: "Felesleges eszkalacio",
};
