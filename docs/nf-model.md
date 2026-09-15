# NF dependency model

Faultline NOC models a minimal 5G standalone core: one gNB, AMF, SMF, UPF and NRF, plus one transport router that every link crosses. This page says what each modelled dependency is, and which 3GPP clause it was checked against. It is a simulated abstraction, not an emulation or a digital twin. There are no real protocol stacks, only the dependency structure.

## Dependencies

| Consumer | Provider | Interface  | What it carries                                     | Checked against                                         |
| -------- | -------- | ---------- | --------------------------------------------------- | ------------------------------------------------------- |
| gNB      | AMF      | N2         | Control plane between the (R)AN and the AMF         | TS 23.501 clause 4.2.7                                  |
| gNB      | UPF      | N3         | User plane between the (R)AN and the UPF            | TS 23.501 clause 4.2.7                                  |
| AMF      | SMF      | N11        | Session management requests from the AMF to the SMF | TS 23.501 clauses 4.2.7 and 6.3.2                       |
| SMF      | UPF      | N4         | Session control of the UPF by the SMF, using PFCP   | TS 23.501 clauses 4.2.7 and 6.3.3.2; TS 29.244 clause 1 |
| AMF      | NRF      | Nnrf (SBI) | NF discovery, for example the AMF finding an SMF    | TS 23.501 clauses 4.2.6 and 6.3.1                       |
| SMF      | NRF      | Nnrf (SBI) | NF discovery, for example the SMF finding a UPF     | TS 23.501 clauses 4.2.6, 6.3.1 and 6.3.3.2              |

The table lives in code as `KIND_DEPENDENCIES` in `faultline_noc/topology.py`. `tests/test_topology.py` fails if the derived graph differs from it.

## What the clauses say

- **Clause 4.2.7, Reference points.** Defines N2 as the reference point between the (R)AN and the AMF, N3 between the (R)AN and the UPF, N4 between the SMF and the UPF, and N11 between the AMF and the SMF.
  Source: https://itecspec.com/3gpp/23.501/s/4.2.7
- **Clause 4.2.6, Service-based interfaces.** Lists Namf, Nsmf and Nnrf as the service-based interfaces the AMF, SMF and NRF expose. In the service-based architecture, N11 is carried by Namf and Nsmf service operations. That is why the simulator's N11 alarm text names `CreateSMContext`.
  Source: https://itecspec.com/3gpp/23.501/s/4.2.6
- **Clause 6.3.1, NF and NF service discovery.** Unless NF information is configured locally, discovery goes through the NRF. NF instances register their NF profile with the NRF, and requester NFs query the NRF.
  Source: https://itecspec.com/3gpp/23.501/s/6.3.1
- **Clause 6.3.2, SMF discovery and selection.** When the AMF does discovery, it uses the NRF to find SMF instances, unless SMF information is available by other means.
  Source: https://itecspec.com/3gpp/23.501/s/6.3.2
- **Clause 6.3.3.2, SMF provisioning of available UPFs.** The SMF may learn about UPFs through local configuration or through a UPF-initiated N4 association. It may optionally use the NRF to discover them.
  Source: https://itecspec.com/3gpp/23.501/s/6.3.3.2
- **TS 29.244 clause 1, Scope.** PFCP is used on the N4 interface, and a PFCP association is set up between an SMF and a UPF.
  Source: https://itecspec.com/3gpp/29.244/s/1
- Full TS 23.501 text (ETSI TS 123 501 V18.11.0): https://www.etsi.org/deliver/etsi_ts/123500_123599/123501/18.11.00_60/ts_123501v181100p.pdf

## Simplifications (deliberate)

- **The NRF dependency is always on.** The spec says discovery via the NRF applies "unless the expected NF and NF service information is locally configured" (6.3.1), and UPF discovery via the NRF is optional (6.3.3.2). The model assumes a deployment that discovers through the NRF.
- **No SCP, UDM, AUSF, PCF, NSSF or CHF.** Charging over Nchf is out of scope. Diameter Gy is an EPC interface, not a 5GC one, so it does not appear here.
- **No N1, N6, N9 or roaming.** The UE, the data network and inter-PLMN paths are not modelled.
- **Symptoms show only on the consumer side, one hop from the fault.** When the UPF is down, the SMF and gNB raise alarms. The AMF does not raise second-order N11 alarms, and providers do not raise their own peer-loss alarms. A real core would show both.
- **One transport router carries every link.** The NetBox-shaped `config/intended_config.json` has one cable from each NF to `rtr-1`, and topology building fails if an NF is not cabled to it.
- **Fault effects are periodic and fully deterministic.** Real crash-loops back off, and real flaps are irregular.

## Fault classes in this slice

| Class                   | Target     | Root node's own signal                                                    | Consumer-side symptoms                              |
| ----------------------- | ---------- | ------------------------------------------------------------------------- | --------------------------------------------------- |
| `nf_crashloop`          | an NF      | `NF_PROCESS_RESTART` alarm (major) at each cycle start, plus an error log | Alarms on every consumer of the target's interfaces |
| `transport_flap`        | the router | `LINK_FLAP` alarm (major) at each cycle start, plus a warning log         | Alarms on every consumer of every dependency        |
| `insufficient_evidence` | none       | none                                                                      | none (noise only)                                   |

Symptom alarm volume depends on the interface. N4 PFCP failures come in bursts of three critical alarms per affected tick. As a result, the SMF is the loudest node in the UPF crash-loop scenario even though the UPF is the root cause.
