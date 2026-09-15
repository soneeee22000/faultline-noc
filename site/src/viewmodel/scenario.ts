import type { ScenarioInfo } from "../types/payload";

const NF_LABELS: Readonly<Record<string, string>> = {
  gnb: "gNB",
  amf: "AMF",
  smf: "SMF",
  upf: "UPF",
  nrf: "NRF",
  rtr: "Router",
};

const FAULT_LABELS: Readonly<Record<string, string>> = {
  nf_crashloop: "crash-loop",
  transport_flap: "transport flap",
};

/** The NF kind label for a node name such as `upf-1`. */
export function nfLabel(node: string): string {
  const kind = node.split("-")[0] ?? node;
  return NF_LABELS[kind] ?? node;
}

/** A short human title for a scenario card, derived from its injected fault. */
export function scenarioTitle(scenario: ScenarioInfo): string {
  const fault = scenario.injected_fault;
  if (fault === null) return "No-fault control";
  const base = `${nfLabel(fault.target)} ${FAULT_LABELS[fault.kind] ?? fault.kind.replaceAll("_", " ")}`;
  return scenario.injection === null ? base : `${base} with log injection`;
}

/** The `sNN` prefix of a scenario id. */
export function shortScenarioId(id: string): string {
  return id.split("_")[0] ?? id;
}
