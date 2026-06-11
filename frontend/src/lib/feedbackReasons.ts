import type { FeedbackReason } from "./types";

export const FEEDBACK_REASON_LABELS: Record<FeedbackReason, string> = {
  pontatlan: "Pontatlan tartalom",
  hianyos: "Hiányos válasz",
  rossz_hangnem: "Nem megfelelő hangnem",
  rossz_forras: "Rossz forrás",
  felesleges_eszkalacio: "Felesleges eszkaláció",
};
