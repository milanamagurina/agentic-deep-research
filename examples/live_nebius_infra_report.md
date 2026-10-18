# What factors beyond GPU model most influence real-world AI infrastructure performance, and how does Nebius address them across compute, networking, storage, and software?

## Answer
**Publicly available evidence is insufficient to rank the non-GPU factors that most influence real-world AI infrastructure performance or to verify how Nebius addresses them across compute, networking, storage, and software.** [1][2][3][4][5][6][7][8]

Evidence status: **INSUFFICIENT EVIDENCE** · model-estimated confidence 35% · evidence sufficiency 21% (H1)

## Why
**1. No available evidence ranks which non-GPU factor most limits real-world AI performance.** [2][3][4][5][6][7][8]
   - Storage claims report throughput figures but no IOPS, latency, data locality, or caching comparisons. [4][5][6][7]
   - Network claims describe passthrough and an NCCL benchmark, not bandwidth, latency, topology, RDMA, or congestion dominance. [5][8]
   - Software claims describe Soperator and KAI Scheduler, not orchestration, driver, compiler, or serving optimization comparisons. [2][3]
**2. Nebius's layer-specific capabilities are documented separately, not as a verified integrated design.** [2][3][4][5][6][7][8]
   - Storage, network, and software capabilities are reported as separate features rather than as a jointly optimized system. [2][3][4][5][6][7][8]
   - No claim demonstrates ablation or bottleneck analysis isolating one layer's contribution. [1][2][3][4][5][6][7][8]
   - The passthrough claim lacks independent confirmation. [8]
**3. Reported metrics are end-to-end outcomes or peaks, so they cannot identify bottlenecks.** [1][3][4][5][6][7]
   - MLPerf training times are end-to-end results for specific models and GPU counts. [1][3][4]
   - Storage figures are per-client or aggregated peaks rather than sustained workload behavior. [4][5][6][7]
   - No claim connects these metrics to a ranked set of non-GPU bottlenecks. [2][3][4][5][6][7][8]

## Caveats
- Source independence: 12 sources with evidence reduce to 2 independent roots; 2 of these are interested parties (self-reported).
- Thinly sourced: 12 of 12 key claims rest on a single independent source.
- Open gap [NO_INDEPENDENT_SOURCE]: C_1902cdcc53: no independent confirmation of 'Nebius runs its virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, resulting in zero performance degradation and parity with bare-metal benchmarks.'
- Open gap [WEAK_INFERENCE]: I_262527880a → H1: needs evidence on 'Comparative bottleneck attribution across compute, storage, software, and network'
- Confidence values are model-estimated evidence beliefs from explicit heuristics, not calibrated probabilities.

## What would change our mind
1. An independent bottleneck or ablation study attributing performance to network, storage, or software layers.
2. Sustained storage and network measurements under representative AI training workloads rather than peak or aggregated figures.
3. Independent validation of Nebius passthrough and benchmark claims.
4. Comparative evidence across providers or configurations that isolates non-GPU factors.
5. Evidence resolving: C_1902cdcc53: no independent confirmation of 'Nebius runs its virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, resulting in zero performance degradation and parity with bare-metal benchmarks.'
6. Evidence resolving: I_262527880a → H1: needs evidence on 'Comparative bottleneck attribution across compute, storage, software, and network'
7. Evidence resolving: I_262527880a → H1: needs evidence on 'Evidence that RDMA/congestion behavior is the dominant limiter'

## Citations you can check
_All 8 cited sources and all 14 quotes the report relies on. Each quote link opens the page at that text (text fragments; plain URL where unsupported). Re-check them all live: `python -m evidence_research.verification.citation_audit report.json`._

**[1]** [MLPerf® Training v5.1: Leading results on NVIDIA Blackwell and Blackwell Ultra systems](https://nebius.com/blog/posts/mlperf-training-v5-1-results) — nebius.com, published unknown
   - SUPPORTS “Nebius recorded a Llama-2-70B LoRA training time of 5.82 minutes on 16x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 1st.”: [“Llama-2-70B LoRA (training time/place)8.48 min / 1st [1]9.55 min / 2nd [2]5.82 min / 1st [3]3.10 min / 1st [4]”](https://nebius.com/blog/posts/mlperf-training-v5-1-results#:~:text=Llama-2-70B%20LoRA%20%28training%20time%2Fplace%298.48%20min,%2F%201st%20%5B4%5D)
   - SUPPORTS “Nebius recorded a FLUX.1 training time of 93.17 minutes on 16x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 1st.”: [“FLUX.1 (training time/place)---93.17 min / 1st [9]”](https://nebius.com/blog/posts/mlperf-training-v5-1-results#:~:text=FLUX.1%20%28training%20time%2Fplace%29---93.17%20min%20%2F%201st%20%5B9%5D)
   - SUPPORTS “Nebius recorded a Llama-3.1-8B training time of 85.37 minutes on 8x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 6th.”: [“Llama-3.1-8B (training time/place)75.84 min / 1st [5]85.37 min / 6th [6]51.83 min / 1st [7]27.83 min / 1st [8]”](https://nebius.com/blog/posts/mlperf-training-v5-1-results#:~:text=Llama-3.1-8B%20%28training%20time%2Fplace%2975.84%20min%20%2F,%2F%201st%20%5B8%5D)
**[2]** [Open-source NVIDIA Run:ai is now available on Nebius AI Cloud Applications](https://nebius.com/blog/posts/nvidia-run-ai-open-source-nebius-applications) — nebius.com, published unknown
   - SUPPORTS “The scheduling core of NVIDIA Run:ai is KAI Scheduler, which has been open source since April 2025 under Apache 2.0 and is a CNCF Sandbox project.”: [“NVIDIA Run:ai is an integrated platform whose scheduling core is KAI Scheduler, open source since April 2025 under Apache 2.0 and a CNCF Sandbox project”](https://nebius.com/blog/posts/nvidia-run-ai-open-source-nebius-applications#:~:text=NVIDIA%20Run%3Aai%20is%20an%20integrated,CNCF%20Sandbox%20project)
**[3]** [Nebius demonstrates industry-leading AI training performance in latest MLPerf® results](https://nebius.com/blog/posts/industry-leading-ai-training-performance-in-mlperf) — nebius.com, published unknown
   - SUPPORTS “Nebius launched its MLPerf Training v5.0 benchmarks using Soperator, its in-house Kubernetes operator for Slurm, in Q2 2025.”: [“we launched these benchmarks by using Soperator, our in-house Kubernetes operator for Slurm. This software enables AI clusters to run with a high level of resiliency and availability, while providing exceptional simplicity for ML operational teams”](https://nebius.com/blog/posts/industry-leading-ai-training-performance-in-mlperf#:~:text=we%20launched%20these%20benchmarks%20by,ML%20operational%20teams)
   - SUPPORTS “Nebius recorded a training step time of 124.5 minutes on a 128-node NVIDIA Hopper cluster when training a Llama 3.1 405B model in MLPerf Training v5.0 in Q2 2025.”: [“We achieved training step times of 124.5 min and 244.6 min for Llama 3.1 405B on the 128-node cluster and 64-node cluster, respectively¹”](https://nebius.com/blog/posts/industry-leading-ai-training-performance-in-mlperf#:~:text=We%20achieved%20training%20step%20times,64-node%20cluster%2C%20respectively%C2%B9)
   - SUPPORTS “Nebius ran the MLPerf Training v5.0 Llama 3.1 405B benchmark on a 64-node cluster with 512 NVIDIA H200 GPUs in Q2 2025.”: [“64-node cluster with 512 NVIDIA H200 GPUs”](https://nebius.com/blog/posts/industry-leading-ai-training-performance-in-mlperf#:~:text=64-node%20cluster%20with%20512%20NVIDIA%20H200%20GPUs)
**[4]** [Q2 2025: Nebius AI Cloud updates](https://nebius.com/blog/posts/q2-2025-nebius-ai-cloud-updates) — nebius.com, published unknown
   - SUPPORTS “Nebius Shared Filesystem achieved 442 GB/s aggregated write performance on a 302-host production cluster in Q2 2025.”: [“on a 302-host production cluster, we achieved 442 GB/s aggregated write and 987 GB/s aggregated read performance”](https://nebius.com/blog/posts/q2-2025-nebius-ai-cloud-updates#:~:text=on%20a%20302-host%20production%20cluster%2C,aggregated%20read%20performance)
   - SUPPORTS “Nebius recorded a training step time of 124.5 minutes on a 128-node NVIDIA Hopper cluster when training a Llama 3.1 405B model in MLPerf Training v5.0 in Q2 2025.”: [“We recorded training step times of 124.5 minutes on a 128-node cluster and 244.6 minutes on a 64-node cluster. This demonstrates the near-linear scaling of Nebius infrastructure — a 1.97x speedup when doubling the cluster size”](https://nebius.com/blog/posts/q2-2025-nebius-ai-cloud-updates#:~:text=We%20recorded%20training%20step%20times,the%20cluster%20size)
**[5]** [Nebius monthly digest: July 2025](https://nebius.com/blog/posts/digest-july-2025) — nebius.com, published unknown
   - SUPPORTS “Nebius Enhanced Object Storage offers up to 10 GB/s write throughput per client.”: [“We launched Enhanced Object Storage, a new performance-focused class of storage. It’s great for streaming datasets and weights to GPU and for checkpointing. The new class offers up to 10 GB/s write throughput per client and unlimited capacity”](https://nebius.com/blog/posts/digest-july-2025#:~:text=We%20launched%20Enhanced%20Object%20Storage%2C,and%20unlimited%20capacity)
   - SUPPORTS “Nebius Soperator documentation describes running an NCCL all-reduce benchmark to test distributed GPU performance in a cluster.”: [“Soperator gets more practical — run Slurm batch jobs with ease and test distributed GPU performance by using an NCCL all-reduce benchmark in your cluster”](https://nebius.com/blog/posts/digest-july-2025#:~:text=Soperator%20gets%20more%20practical%20%E2%80%94,in%20your%20cluster)
**[6]** [nebius-rush/docs/01-nebius-platform-overview.md at master ...](https://github.com/Sprit3Dan/nebius-rush/blob/master/docs/01-nebius-platform-overview.md) — github.com, published unknown
   - SUPPORTS “Nebius Shared Filesystem achieved 442 GB/s aggregated write performance on a 302-host production cluster in Q2 2025.”: [“POSIX shared filesystem for AI workloads; up to **~100 GB/s** class throughput and ~1M IOPS, scalable volume (public benchmark: 442 GB/s aggregate on a 302-host cluster)”](https://github.com/Sprit3Dan/nebius-rush/blob/master/docs/01-nebius-platform-overview.md)
**[7]** [We’re launching a new Nebius platform built from the ground up](https://nebius.com/blog/posts/we-launch-a-new-ai-platform) — nebius.com, published unknown
   - SUPPORTS “Nebius new platform file storage delivers up to 100 GBps aggregated read throughput.”: [“boosting performance to up to 100 GBps and 1M IOPS for aggregated read operations”](https://nebius.com/blog/posts/we-launch-a-new-ai-platform#:~:text=boosting%20performance%20to%20up%20to,aggregated%20read%20operations)
**[8]** [Nebius proves bare-metal-class performance for AI inference workloads in MLPerf® Inference](https://nebius.com/blog/posts/bare-metal-class-performance-mlperf-inference) — nebius.com, published unknown
   - SUPPORTS “Nebius runs its virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, resulting in zero performance degradation and parity with bare-metal benchmarks.”: [“We run our virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, which results in zero performance degradation and allows us to stay on par with the best industry benchmarks”](https://nebius.com/blog/posts/bare-metal-class-performance-mlperf-inference#:~:text=We%20run%20our%20virtual%20GPU,best%20industry%20benchmarks)

## How the agent decided
_Decisions made by code during the run, in order, with their reasons._

1. agent selected: Next agent: GeneralResearcher (utility 0.95). Reason: no evidence collected yet: broad discovery first
2. independence summary: 6 URLs with evidence → 2 publication families → 2 independent evidence roots; 2 of them are interested parties (self-reported)
3. inference rejected: I_262527880a needs_evidence (weak): The premises show network communication is an optimizable factor, but they do not establish that real-world AI performance is primarily network-bound or best explained by fabric design
4. inference rejected: I_959fd58892 rejected (weak): The premises support storage as a performance factor, but throughput claims alone do not establish that storage is the primary constraint or best explanation.; missing: IOPS, latency, data l
5. inference rejected: I_76c1c8c5de rejected (weak): The premises support scheduling and general cloud software capabilities, but they do not substantiate the broader software-layer primacy claimed in the conclusion.; missing: Evidence for dri
6. inference rejected: I_104258faa2 needs_evidence (plausible): The premises directly describe vertical integration and full-stack control across components, supporting joint optimization, though they do not independently prove it is the best 
7. agent selected: Next agent: IndependenceResearcher (utility 1.00). Reason: [NO_INDEPENDENT_SOURCE] C_1ea9b20797: no independent confirmation of 'Nebius recorded a training step time of 124.5 minutes on a 128-node NVIDIA Hopper cluster w
8. agent selected: Next agent: GapResearcher (utility 1.00). Reason: [MISSING_REQUIRED_DIMENSION] H4.R2 (H4): no evidence yet on 'Ablation or comparative benchmarks isolating the effect of integrated stack changes versus individual-layer c
9. stop decision: CONTINUE: 15 critical claim(s) below sufficiency, 0 open contradiction(s), 25 researchable gap(s); new independent roots this round: 2
10. contradiction found: S_596f74076d contradicts C_cbc9955887: "Nebius also demonstrated excellent scaling on HGX B200 systems, increasing cluster size fr"
11. independence summary: 9 URLs with evidence → 3 publication families → 2 independent evidence roots; 2 of them are interested parties (self-reported)
12. independence summary: 12 URLs with evidence → 3 publication families → 2 independent evidence roots; 2 of them are interested parties (self-reported)
13. stop decision: STOP (DIMINISHING_RETURNS): last research round produced no new independent evidence root; new independent roots this round: 0

---

# Supporting detail


## Surviving hypotheses
| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |
|---|---|---|---|---|---|---|
| H5 | Publicly available information is insufficient to rank the non-GPU factors most affecting real-world AI infrastructure performance or to verify how Nebius addresses them across compute, networking, storage, and software. (null) | 35% | **75%** | 100% | n/a | supported |
| H1 | Real-world AI infrastructure performance is primarily constrained by east-west network bandwidth, latency, topology, and RDMA/congestion behavior; Nebius's performance is best explained by how its network fabric is designed and configured. | 35% | **35%** | 21% | n/a | insufficient |
| H2 | Real-world AI infrastructure performance is primarily constrained by storage throughput, IOPS, latency, data locality, and caching/tiering; Nebius's performance is best explained by its storage architecture and data-path design. | 35% | **35%** | 21% | n/a | insufficient |
| H3 | Real-world AI infrastructure performance is primarily constrained by orchestration, scheduling, driver/kernel/compiler optimization, MLOps tooling, and serving software; Nebius's performance is best explained by its software-layer capabilities and optimizations. | 35% | **35%** | 25% | n/a | insufficient |
| H4 | Real-world AI infrastructure performance is not determined by any single layer but by co-design across compute, networking, storage, and software; Nebius's performance is best explained by integration and joint optimization across these layers. | 35% | **35%** | 25% | n/a | insufficient |

Main surviving hypothesis: **H1** — Real-world AI infrastructure performance is primarily constrained by east-west network bandwidth, latency, topology, and RDMA/congestion behavior; Nebius's performance is best explained by how its network fabric is designed and configured.
Strongest counter-hypothesis: **H2** — Real-world AI infrastructure performance is primarily constrained by storage throughput, IOPS, latency, data locality, and caching/tiering; Nebius's performance is best explained by its storage architecture and data-path design.

## Rejected / weakened hypotheses
- None.
  - H1 inference not accepted: I_262527880a (needs_evidence): Topology-aware scheduling improved NCCL performance, Nebius documents NCCL all-reduce benchmarking, and its platform includes GPU-to-GPU networking, indicating network communication behavior is an optimizable performance factor. — The premises show network communication is an optimizable factor, but they do not establish that real-world AI performance is primarily network-bound or best explained by fabric design.; R3: causal/abductive inference with unexcluded confounders
  - H1 inference not accepted: I_b2f3015e57 (rejected): The breadth of high-throughput storage and data-path claims indicates storage is also a major factor, challenging the view that performance is primarily network-bound. — The premises are storage-focused and challenge, rather than support, the conclusion that performance is primarily network-bound.
  - H1 inference not accepted: I_f5431a8eaa (needs_evidence): Documented storage throughput and caching plus scheduling software indicate that non-network layers also substantially influence Nebius performance, weakening network fabric design as the primary explanation. — The premises document storage throughput, caching, and scheduling capabilities, not network fabric dominance; they do not establish that network design is the primary constraint or best explanation.; R3: causal/abductive inference with unexcluded confounders
  - H2 inference not accepted: I_959fd58892 (rejected): Multiple Nebius storage systems report high aggregated or per-client throughput plus data-path optimizations, indicating storage architecture is a significant performance factor. — The premises support storage as a performance factor, but throughput claims alone do not establish that storage is the primary constraint or best explanation.
  - H2 inference not accepted: I_a41c4dab43 (needs_evidence): NCCL all-reduce benchmarking, bare-metal InfiniBand passthrough, and scheduling software indicate that network and software layers also matter, weakening storage architecture as the primary explanation. — The premises concern NCCL networking, bare-metal GPU/InfiniBand passthrough, and scheduling software, not storage dominance; they do not establish storage architecture as the primary constraint or best explanation.; R3: causal/abductive inference with unexcluded confounders
  - H3 inference not accepted: I_76c1c8c5de (rejected): Nebius evidences scheduling and cloud software capabilities, but not driver, kernel, compiler, or serving optimizations, so software-layer primacy is only weakly supported. — The premises support scheduling and general cloud software capabilities, but they do not substantiate the broader software-layer primacy claimed in the conclusion.
  - H3 inference not accepted: I_34d5a3b188 (needs_evidence): Network benchmarking and passthrough together with storage throughput indicate that non-software layers also matter, weakening software-layer capabilities as the primary explanation. — The premises document storage throughput and network benchmarking/passthrough, not software-layer dominance; they do not establish software capabilities as the primary constraint or best explanation.; R3: causal/abductive inference with unexcluded confounders
  - H4 inference not accepted: I_104258faa2 (needs_evidence): Nebius describes vertical integration and full-stack control across compute, storage, networking, and managed services, supporting joint optimization rather than a single-layer explanation. — The premises directly describe vertical integration and full-stack control across components, supporting joint optimization, though they do not independently prove it is the best explanation.; R3: causal/abductive inference with unexcluded confounders
  - H4 inference not accepted: I_317cabe291 (rejected): Training step time approximately halves when doubling nodes, suggesting efficient distributed scaling that depends on integration beyond GPU count. — Two step times showing near-linear scaling suggest efficient distributed execution, but they do not establish that integration across layers is the primary explanation.
  - H4 inference not accepted: I_641535cb52 (needs_evidence): Evidence spanning NCCL networking, bare-metal GPU and InfiniBand passthrough, storage throughput, scheduling software, and storage caching jointly supports co-design across layers rather than a single-layer explanation. — The premises show capabilities across several layers, but they do not demonstrate integration, joint optimization, or relative contribution; concluding co-design is an unsupported leap.; R3: causal/abductive inference with unexcluded confounders

## Critical claims: supporting and contradicting evidence
#### C_3bbff40a7f: Nebius recorded a Llama-2-70B LoRA training time of 5.82 minutes on 16x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 1st.
- Model-estimated posterior **56%** · evidence sufficiency **50%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [1]: “Llama-2-70B LoRA (training time/place)8.48 min / 1st [1]9.55 min / 2nd [2]5.82 min / 1st [3]3.10 min / 1st [4]” — source 0.36 · independence 0.50 · LR 1.25
- MISSING: C_3bbff40a7f: no independent confirmation of 'Nebius recorded a Llama-2-70B LoRA training time of 5.82 minutes on 16x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 1st.'

#### C_1cd47f53a1: The scheduling core of NVIDIA Run:ai is KAI Scheduler, which has been open source since April 2025 under Apache 2.0 and is a CNCF Sandbox project.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: 2025-04-01 → …
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [2]: “NVIDIA Run:ai is an integrated platform whose scheduling core is KAI Scheduler, open source since April 2025 under Apache 2.0 and a CNCF Sandbox project” — source 0.41 · independence 1.00 · LR 2
- MISSING: C_1cd47f53a1: no independent confirmation of 'The scheduling core of NVIDIA Run:ai is KAI Scheduler, which has been open source since April 2025 under Apache 2.0 and is a CNCF Sandbox project.'

#### C_1ea9b20797: Nebius recorded a training step time of 124.5 minutes on a 128-node NVIDIA Hopper cluster when training a Llama 3.1 405B model in MLPerf Training v5.0 in Q2 2025.
- Model-estimated posterior **56%** · evidence sufficiency **50%** · status `insufficient` · period: period unknown
- Raw sources: 5 · independent roots: **1** · history: 0.50 → 0.56 → 0.61 → 0.56
- SUPPORT [3]: “We achieved training step times of 124.5 min and 244.6 min for Llama 3.1 405B on the 128-node cluster and 64-node cluster, respectively¹” — source 0.36 · independence 0.50 · LR 1.25
- SUPPORT [4]: “We recorded training step times of 124.5 minutes on a 128-node cluster and 244.6 minutes on a 64-node cluster. This demonstrates the near-linear scaling of Nebius infrastructure — a 1.97x speedup when doubling the cluster size” — source 0.36 · independence 0.50 · LR 1.25
- MISSING: C_1ea9b20797: 5 sources but only 1 independent root

#### C_2b007641b8: Nebius Enhanced Object Storage offers up to 10 GB/s write throughput per client.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [5]: “We launched Enhanced Object Storage, a new performance-focused class of storage. It’s great for streaming datasets and weights to GPU and for checkpointing. The new class offers up to 10 GB/s write throughput per client and unlimited capacity” — source 0.41 · independence 0.50 · LR 2
- MISSING: C_2b007641b8: no independent confirmation of 'Nebius Enhanced Object Storage offers up to 10 GB/s write throughput per client.'

#### C_04c5a3f87c: Nebius Shared Filesystem achieved 442 GB/s aggregated write performance on a 302-host production cluster in Q2 2025.
- Model-estimated posterior **56%** · evidence sufficiency **50%** · status `insufficient` · period: period unknown
- Raw sources: 3 · independent roots: **1** · history: 0.50 → 0.56 → 0.61 → 0.56
- SUPPORT [4]: “on a 302-host production cluster, we achieved 442 GB/s aggregated write and 987 GB/s aggregated read performance” — source 0.36 · independence 0.50 · LR 1.25
- SUPPORT [6]: “POSIX shared filesystem for AI workloads; up to **~100 GB/s** class throughput and ~1M IOPS, scalable volume (public benchmark: 442 GB/s aggregate on a 302-host cluster)” — source 0.32 · independence 0.40 · LR 1.25
- MISSING: C_04c5a3f87c: 3 sources but only 1 independent root

#### C_0fcd11db8a: Nebius new platform file storage delivers up to 100 GBps aggregated read throughput.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [7]: “boosting performance to up to 100 GBps and 1M IOPS for aggregated read operations” — source 0.41 · independence 0.50 · LR 2
- MISSING: C_0fcd11db8a: no independent confirmation of 'Nebius new platform file storage delivers up to 100 GBps aggregated read throughput.'

#### C_15f01f21f1: Nebius Soperator documentation describes running an NCCL all-reduce benchmark to test distributed GPU performance in a cluster.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [5]: “Soperator gets more practical — run Slurm batch jobs with ease and test distributed GPU performance by using an NCCL all-reduce benchmark in your cluster” — source 0.41 · independence 0.50 · LR 2
- MISSING: C_15f01f21f1: no independent confirmation of 'Nebius Soperator documentation describes running an NCCL all-reduce benchmark to test distributed GPU performance in a cluster.'

#### C_1902cdcc53: Nebius runs its virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, resulting in zero performance degradation and parity with bare-metal benchmarks.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [8]: “We run our virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, which results in zero performance degradation and allows us to stay on par with the best industry benchmarks” — source 0.41 · independence 0.50 · LR 2
- MISSING: C_1902cdcc53: no independent confirmation of 'Nebius runs its virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, resulting in zero performance degradation and parity with bare-metal benchmarks.'

#### C_372f045886: Nebius ran the MLPerf Training v5.0 Llama 3.1 405B benchmark on a 64-node cluster with 512 NVIDIA H200 GPUs in Q2 2025.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [3]: “64-node cluster with 512 NVIDIA H200 GPUs” — source 0.41 · independence 0.50 · LR 2
- MISSING: C_372f045886: no independent confirmation of 'Nebius ran the MLPerf Training v5.0 Llama 3.1 405B benchmark on a 64-node cluster with 512 NVIDIA H200 GPUs in Q2 2025.'

#### C_3bd36499b9: Nebius recorded a FLUX.1 training time of 93.17 minutes on 16x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 1st.
- Model-estimated posterior **56%** · evidence sufficiency **50%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [1]: “FLUX.1 (training time/place)---93.17 min / 1st [9]” — source 0.36 · independence 0.50 · LR 1.25
- MISSING: C_3bd36499b9: no independent confirmation of 'Nebius recorded a FLUX.1 training time of 93.17 minutes on 16x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 1st.'

#### C_180a3b5095: Nebius recorded a Llama-3.1-8B training time of 85.37 minutes on 8x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 6th.
- Model-estimated posterior **56%** · evidence sufficiency **50%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [1]: “Llama-3.1-8B (training time/place)75.84 min / 1st [5]85.37 min / 6th [6]51.83 min / 1st [7]27.83 min / 1st [8]” — source 0.36 · independence 0.50 · LR 1.25
- MISSING: C_180a3b5095: no independent confirmation of 'Nebius recorded a Llama-3.1-8B training time of 85.37 minutes on 8x NVIDIA HGX B200 GPUs in MLPerf Training v5.1, placing 6th.'

#### C_0baaa9d94a: Nebius launched its MLPerf Training v5.0 benchmarks using Soperator, its in-house Kubernetes operator for Slurm, in Q2 2025.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [3]: “we launched these benchmarks by using Soperator, our in-house Kubernetes operator for Slurm. This software enables AI clusters to run with a high level of resiliency and availability, while providing exceptional simplicity for ML operational teams” — source 0.41 · independence 0.50 · LR 2
- MISSING: C_0baaa9d94a: no independent confirmation of 'Nebius launched its MLPerf Training v5.0 benchmarks using Soperator, its in-house Kubernetes operator for Slurm, in Q2 2025.'

## Source independence
**12 URLs with evidence → 3 publication families → 2 independent evidence roots.**
- Root S_90651928f4 (Nebius and Saturn Cloud launch first-in-class AI MLOps cloud): 11 sources S_08bc752e5f, S_1d3177d568, S_596f74076d, S_5ab629bd5b, S_5c31d5b986, S_7e0de3d977, S_90651928f4, S_a95e408133, S_b9d968a7d4, S_fa6d3d3570, S_fbb78fded9
- 30 source(s) screened out before extraction, e.g. S_41df1a3603 (duplicate source: same title on the same site as S_71ef69431); S_fab68daeac (duplicate source: same title on the same site as S_763e2392f); S_a40fdf1570 (Duplicate of S_90651928f4 (same Nebius/Saturn Cloud announce)

## Scientific study quality
- No scientific studies among the sources.

## Research gaps
- **HIGH** [NO_INDEPENDENT_SOURCE] C_1902cdcc53: no independent confirmation of 'Nebius runs its virtual GPU instances without virtualizing NVIDIA GPUs and NVIDIA ConnectX InfiniBand adapters, resulting in zero performance degradation and parity with bare-metal benchmarks.'
- **HIGH** [WEAK_INFERENCE] I_262527880a → H1: needs evidence on 'Comparative bottleneck attribution across compute, storage, software, and network'
- **HIGH** [WEAK_INFERENCE] I_262527880a → H1: needs evidence on 'Evidence that RDMA/congestion behavior is the dominant limiter'
- **HIGH** [WEAK_INFERENCE] I_959fd58892 → H2: needs evidence on 'IOPS, latency, data locality, and caching/tiering evidence'
- **HIGH** [WEAK_INFERENCE] I_959fd58892 → H2: needs evidence on 'Sustained rather than peak or aggregated throughput'
- **HIGH** [WEAK_INFERENCE] I_76c1c8c5de → H3: needs evidence on 'Evidence for driver, kernel, compiler, MLOps, or serving optimizations'
- **HIGH** [WEAK_INFERENCE] I_76c1c8c5de → H3: needs evidence on 'Comparative attribution showing software-layer dominance'
- **HIGH** [WEAK_INFERENCE] I_104258faa2 → H4: needs evidence on 'Independent benchmarks isolating integration effects from individual components'
- **HIGH** [WEAK_INFERENCE] I_104258faa2 → H4: needs evidence on 'Component-level attribution across workloads'
- **HIGH** [WEAK_INFERENCE] I_317cabe291 → H4: needs evidence on 'Scaling-efficiency metrics beyond two step times'

## Why research stopped
- DIMINISHING_RETURNS: last research round produced no new independent evidence root
- Final agent bids: IndependenceResearcher 1.00, GapResearcher 1.00, AdversarialResearcher 0.66, GeneralResearcher 0.21, PrimarySourceResearcher 0.00, ContradictionResearcher 0.00, ReplicationResearcher 0.00, Synthesis 0.00

## Limitations and method
- Hypothesis-first research: competing hypotheses and evidence requirements were generated before searching.
- LLMs proposed claims, stances and inferences; code verified excerpts verbatim, counted sources and computed every score.
- Probabilities are model-estimated evidence beliefs from heuristic likelihood ratios, NOT calibrated probabilities.
- Evidence from one provenance cluster counts once; derivatives add 15% of their weight.
- Source credibility uses heuristic priors by source type, adjusted per claim category; no audited ratings.
- Scientific evidence is weighted by a deterministic study-quality score and replication factors; peer review alone is not decisive.
- Research agents were chosen each round by heuristic utility bids, not by a fixed pipeline.
- 30 source(s) were screened out before extraction; reasons are preserved (negative provenance).
- Stop reason: DIMINISHING_RETURNS — last research round produced no new independent evidence root

## All citations
[1] MLPerf® Training v5.1: Leading results on NVIDIA Blackwell and Blackwell Ultra systems — https://nebius.com/blog/posts/mlperf-training-v5-1-results (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[2] Open-source NVIDIA Run:ai is now available on Nebius AI Cloud Applications — https://nebius.com/blog/posts/nvidia-run-ai-open-source-nebius-applications (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[3] Nebius demonstrates industry-leading AI training performance in latest MLPerf® results — https://nebius.com/blog/posts/industry-leading-ai-training-performance-in-mlperf (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[4] Q2 2025: Nebius AI Cloud updates — https://nebius.com/blog/posts/q2-2025-nebius-ai-cloud-updates (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[5] Nebius monthly digest: July 2025 — https://nebius.com/blog/posts/digest-july-2025 (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[6] nebius-rush/docs/01-nebius-platform-overview.md at master ... — https://github.com/Sprit3Dan/nebius-rush/blob/master/docs/01-nebius-platform-overview.md (github.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[7] We’re launching a new Nebius platform built from the ground up — https://nebius.com/blog/posts/we-launch-a-new-ai-platform (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)
[8] Nebius proves bare-metal-class performance for AI inference workloads in MLPerf® Inference v5.1 — https://nebius.com/blog/posts/bare-metal-class-performance-mlperf-inference (nebius.com; published unknown; retrieved 2026-10-18; root S_90651928f4)

_Stats: {'iterations': 2, 'searches': 10, 'extractions': 12, 'model_calls': 41, 'hypothesis': 5, 'requirement': 16, 'source': 68, 'claim': 120, 'evidence': 143, 'inference': 10, 'gap': 37, 'edges': 598, 'screened_out': 30, 'unverified_evidence': 0}_