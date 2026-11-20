# PICALIB results log

Appended automatically by each notebook.


---
## nb01: the guard panel on public sets (Liu 2610.03448 rebuilds) and this paper's sets
_2026-11-19 21:01_

```
Notebook 01: the guard panel on public sets. Measurement only.

ours_bipia:hijack      best released: PIGuard caught 0.920 [0.856, 0.961]
ours_bipia:harmful     best released: Wolf Defender caught 0.950 [0.889, 1.000]
ours_opi               best released: fmops DistilBERT caught 0.901 [0.810, 0.947]
ours_agentdojo:all     best released: Wolf Defender caught 0.915 [0.901, 0.930]
admatched              best released: Wolf Defender caught 0.882 [0.818, 0.941]
adshift                best released: Wolf Defender caught 0.882 [0.818, 0.941]
bipia_pairs            best released: PIGuard caught 0.951 [0.932, 0.962]
tbeval                 best released: Horizon-Labs (Oct 2026 weights) caught 1.000 [1.000, 1.000]

released detectors at or above 0.90 on the BIPIA pairs and 0.80 on AD-Matched (Liu rule): none

bar for notebook 03 (reports/bar_03.json): Horizon-Labs (Oct 2026 weights) AD-Matched caught 0.843, AD-Shift 0.878
failed detectors: ['protectai-small-v2', 'qualifire-sentinel', 'wani-aug:trunc', 'wani-aug:win', 'wani-conventional:trunc', 'wani-conventional:win', 'wani-full-s0:trunc', 'wani-full-s0:win', 'wani-full-s1:trunc', 'wani-full-s1:win', 'wani-full-s2:trunc', 'wani-full-s2:win', 'wani-notwin:trunc', 'wani-notwin:win', 'wani-sizematched:trunc', 'wani-sizematched:win']

set                              ours_bipia:hijack  ours_bipia:harmful  ours_opi  ours_agentdojo:all  admatched  adshift  bipia_pairs  tbeval
detector_name                                                                                                                                
Horizon-Labs (Oct 2026 weights)              0.320               0.950     0.389               0.814      0.843    0.878        0.377   1.000
Horizon-Labs (current weights)               0.420               0.950     0.277               0.749      0.738    0.785        0.448   0.997
InjecGuard                                   0.920               0.933     0.210               0.252      0.021    0.064        0.951   0.527
JasperLS                                     0.027               0.133     0.071               0.127      0.208    0.219        0.049   0.187
PIGuard                                      0.920               0.933     0.210               0.252      0.021    0.064        0.951   0.527
Prismor-1.5B                                 0.087               0.050     0.000               0.683      0.755    0.822        0.036   0.159
Prompt-Guard-2 22M                           0.307               0.617     0.642               0.709      0.590    0.631        0.317   0.608
Prompt-Guard-2 86M                           0.053               0.400     0.539               0.730      0.715    0.790        0.104   0.579
ProtectAI v1                                 0.007               0.000     0.287               0.057      0.021    0.067        0.004   0.233
ProtectAI v2                                 0.000               0.017     0.077               0.037      0.028    0.011        0.007   0.101
Sheltron 68M                                 0.873               0.950     0.273               0.213      0.188    0.238        0.572   0.952
TestSavant L                                 0.047               0.800     0.317               0.321      0.312    0.226        0.163   0.245
Wolf Defender                                0.920               0.950     0.447               0.915      0.882    0.882        0.835   1.000
deepset DeBERTa                              0.027               0.133     0.071               0.127      0.208    0.219        0.049   0.187
fmops DistilBERT                             0.013               0.017     0.901               0.223      0.340    0.540        0.022   0.848
```


---
## nb01: the guard panel on public sets (Liu 2610.03448 rebuilds) and this paper's sets
_2026-11-19 21:40_

```
Notebook 01: the guard panel on public sets. Measurement only.

ours_bipia:hijack      best released: PIGuard caught 0.920 [0.856, 0.961]
ours_bipia:harmful     best released: Wolf Defender caught 0.950 [0.889, 1.000]
ours_opi               best released: fmops DistilBERT caught 0.901 [0.810, 0.947]
ours_agentdojo:all     best released: Wolf Defender caught 0.915 [0.901, 0.930]
admatched              best released: Wolf Defender caught 0.882 [0.818, 0.941]
adshift                best released: Wolf Defender caught 0.882 [0.818, 0.941]
bipia_pairs            best released: PIGuard caught 0.951 [0.932, 0.962]
tbeval                 best released: Horizon-Labs (Oct 2026 weights) caught 1.000 [1.000, 1.000]

released detectors at or above 0.90 on the BIPIA pairs and 0.80 on AD-Matched (Liu rule): none

injection slots caught at 1 percent (Liu rule) on AD-Matched and AD-Shift (144 slots each):
  ProtectAI v1                         slots caught: matched   9, shift  35, both   9
  ProtectAI v2                         slots caught: matched  12, shift   8, both   8
  Prompt-Guard-2 86M                   slots caught: matched  97, shift  97, both  97
  Prompt-Guard-2 22M                   slots caught: matched  97, shift  97, both  97
  deepset DeBERTa                      slots caught: matched  40, shift  40, both  39
  fmops DistilBERT                     slots caught: matched  56, shift  87, both  56
  PIGuard                              slots caught: matched   9, shift  34, both   9
  Horizon-Labs (Oct 2026 weights)      slots caught: matched  97, shift  97, both  97
  Horizon-Labs (current weights)       slots caught: matched  95, shift  97, both  95
  Wolf Defender                        slots caught: matched  97, shift  97, both  97
  Prismor-1.5B                         slots caught: matched  92, shift  92, both  92
  Sheltron 68M                         slots caught: matched  55, shift  84, both  55
  TestSavant L                         slots caught: matched  71, shift  49, both  46
  InjecGuard                           slots caught: matched   9, shift  34, both   9
  JasperLS                             slots caught: matched  40, shift  40, both  39

strongest released guard overall: Wolf Defender (mean caught 0.828); its numbers are the bar for notebook 03:
  ours_bipia:hijack      caught 0.920 [0.874, 0.959]  AUROC 0.993
  ours_bipia:harmful     caught 0.950 [0.889, 1.000]  AUROC 0.993
  ours_opi               caught 0.447 [0.378, 0.491]  AUROC 0.884
  ours_agentdojo:all     caught 0.915 [0.901, 0.930]  AUROC 0.996
  admatched              caught 0.882 [0.818, 0.941]  AUROC 0.898
  adshift                caught 0.882 [0.818, 0.941]  AUROC 0.898
  bipia_pairs            caught 0.835 [0.814, 0.850]  AUROC 0.956
  tbeval                 caught 1.000 [1.000, 1.000]  AUROC 1.000

failed detectors: ['protectai-small-v2', 'qualifire-sentinel', 'wani-aug:trunc', 'wani-aug:win', 'wani-conventional:trunc', 'wani-conventional:win', 'wani-full-s0:trunc', 'wani-full-s0:win', 'wani-full-s1:trunc', 'wani-full-s1:win', 'wani-full-s2:trunc', 'wani-full-s2:win', 'wani-notwin:trunc', 'wani-notwin:win', 'wani-sizematched:trunc', 'wani-sizematched:win']

set                              ours_bipia:hijack  ours_bipia:harmful  ours_opi  ours_agentdojo:all  admatched  adshift  bipia_pairs  tbeval
detector_name                                                                                                                                
Horizon-Labs (Oct 2026 weights)              0.320               0.950     0.389               0.814      0.843    0.878        0.377   1.000
Horizon-Labs (current weights)               0.420               0.950     0.277               0.749      0.738    0.785        0.448   0.997
InjecGuard                                   0.920               0.933     0.210               0.252      0.021    0.064        0.951   0.527
JasperLS                                     0.027               0.133     0.071               0.127      0.208    0.219        0.049   0.187
PIGuard                                      0.920               0.933     0.210               0.252      0.021    0.064        0.951   0.527
Prismor-1.5B                                 0.087               0.050     0.000               0.683      0.755    0.822        0.036   0.159
Prompt-Guard-2 22M                           0.307               0.617     0.642               0.709      0.590    0.631        0.317   0.608
Prompt-Guard-2 86M                           0.053               0.400     0.539               0.730      0.715    0.790        0.104   0.579
ProtectAI v1                                 0.007               0.000     0.287               0.057      0.021    0.067        0.004   0.233
ProtectAI v2                                 0.000               0.017     0.077               0.037      0.028    0.011        0.007   0.101
Sheltron 68M                                 0.873               0.950     0.273               0.213      0.188    0.238        0.572   0.952
TestSavant L                                 0.047               0.800     0.317               0.321      0.312    0.226        0.163   0.245
Wolf Defender                                0.920               0.950     0.447               0.915      0.882    0.882        0.835   1.000
deepset DeBERTa                              0.027               0.133     0.071               0.127      0.208    0.219        0.049   0.187
fmops DistilBERT                             0.013               0.017     0.901               0.223      0.340    0.540        0.022   0.848
```


---
## nb01: the guard panel on public sets (Liu 2610.03448 rebuilds) and this paper's sets
_2026-11-20 00:12_

```
Notebook 01: the guard panel on public sets. Measurement only.

ours_bipia:hijack      best released: PIGuard caught 0.920 [0.856, 0.961]
ours_bipia:harmful     best released: Wolf Defender caught 0.950 [0.889, 1.000]
ours_opi               best released: fmops DistilBERT caught 0.901 [0.810, 0.947]
ours_agentdojo:all     best released: Wolf Defender caught 0.915 [0.901, 0.930]
admatched              best released: Wolf Defender caught 0.882 [0.818, 0.941]
adshift                best released: Wolf Defender caught 0.882 [0.818, 0.941]
bipia_pairs            best released: PIGuard caught 0.951 [0.932, 0.962]
tbeval                 best released: Horizon-Labs (Oct 2026 weights) caught 1.000 [1.000, 1.000]

released detectors at or above 0.90 on the BIPIA pairs and 0.80 on AD-Matched (Liu rule): none

this project's guard (seed 0, windowed):
  ours_bipia:hijack      caught 0.887 [0.832, 0.938]  AUROC 0.964
  ours_bipia:harmful     caught 1.000 [0.984, 1.000]  AUROC 1.000
  ours_opi               caught 0.973 [0.960, 0.984]  AUROC 0.995
  ours_agentdojo:all     caught 0.169 [0.151, 0.193]  AUROC 0.832
  admatched              caught 0.329 [0.280, 0.385]  AUROC 0.660
  adshift                caught 0.282 [0.235, 0.342]  AUROC 0.652
  bipia_pairs            caught 0.638 [0.617, 0.658]  AUROC 0.756
  tbeval                 caught 0.464 [0.384, 0.597]  AUROC 0.915

difference ours minus Wolf Defender, caught at 1 percent (Liu rule), cluster bootstrap:
  admatched      -0.553 [-0.612, -0.492]
  adshift        -0.600 [-0.668, -0.531]
  bipia_pairs    -0.197 [-0.219, -0.172]
  tbeval         -0.536 [-0.616, -0.403]

difference ours minus Horizon-Labs (Oct 2026 weights), caught at 1 percent (Liu rule), cluster bootstrap:
  admatched      -0.514 [-0.579, -0.410]
  adshift        -0.596 [-0.662, -0.522]
  bipia_pairs    +0.261 [+0.206, +0.325]
  tbeval         -0.536 [-0.616, -0.403]

identification interval of the 1 percent threshold for this guard: AD-Matched (585 benign) width 0.021; notebook 25 set (129 benign) width 0.005

injection slots caught at 1 percent (Liu rule) on AD-Matched and AD-Shift (144 slots each):
  ProtectAI v1                         slots caught: matched   9, shift  35, both   9
  ProtectAI v2                         slots caught: matched  12, shift   8, both   8
  Prompt-Guard-2 86M                   slots caught: matched  97, shift  97, both  97
  Prompt-Guard-2 22M                   slots caught: matched  97, shift  97, both  97
  deepset DeBERTa                      slots caught: matched  40, shift  40, both  39
  fmops DistilBERT                     slots caught: matched  56, shift  87, both  56
  PIGuard                              slots caught: matched   9, shift  34, both   9
  Horizon-Labs (Oct 2026 weights)      slots caught: matched  97, shift  97, both  97
  Horizon-Labs (current weights)       slots caught: matched  95, shift  97, both  95
  Wolf Defender                        slots caught: matched  97, shift  97, both  97
  Prismor-1.5B                         slots caught: matched  92, shift  92, both  92
  Sheltron 68M                         slots caught: matched  55, shift  84, both  55
  TestSavant L                         slots caught: matched  71, shift  49, both  46
  InjecGuard                           slots caught: matched   9, shift  34, both   9
  JasperLS                             slots caught: matched  40, shift  40, both  39
  Matched-pair guard (seed 0), windowed slots caught: matched  80, shift  76, both  72

strongest released guard overall: Wolf Defender (mean caught 0.828); its numbers are the bar for notebook 03:
  ours_bipia:hijack      caught 0.920 [0.874, 0.959]  AUROC 0.993
  ours_bipia:harmful     caught 0.950 [0.889, 1.000]  AUROC 0.993
  ours_opi               caught 0.447 [0.378, 0.491]  AUROC 0.884
  ours_agentdojo:all     caught 0.915 [0.901, 0.930]  AUROC 0.996
  admatched              caught 0.882 [0.818, 0.941]  AUROC 0.898
  adshift                caught 0.882 [0.818, 0.941]  AUROC 0.898
  bipia_pairs            caught 0.835 [0.814, 0.850]  AUROC 0.956
  tbeval                 caught 1.000 [1.000, 1.000]  AUROC 1.000

failed detectors: ['protectai-small-v2', 'qualifire-sentinel']

set                                     ours_bipia:hijack  ours_bipia:harmful  ours_opi  ours_agentdojo:all  admatched  adshift  bipia_pairs  tbeval
detector_name                                                                                                                                       
Conventional fine-tune, truncated                   0.020               0.033     0.008               0.318      0.433    0.625        0.018   0.863
Conventional fine-tune, windowed                    0.020               0.033     0.008               0.323      0.477    0.664        0.020   0.890
Horizon-Labs (Oct 2026 weights)                     0.320               0.950     0.389               0.814      0.843    0.878        0.377   1.000
Horizon-Labs (current weights)                      0.420               0.950     0.277               0.749      0.738    0.785        0.448   0.997
InjecGuard                                          0.920               0.933     0.210               0.252      0.021    0.064        0.951   0.527
JasperLS                                            0.027               0.133     0.071               0.127      0.208    0.219        0.049   0.187
Matched-pair guard (seed 0), truncated              0.860               0.933     0.973               0.168      0.301    0.257        0.626   0.349
Matched-pair guard (seed 0), windowed               0.887               1.000     0.973               0.169      0.329    0.282        0.638   0.464
Matched-pair guard (seed 1), truncated              0.853               0.933     0.984               0.431      0.225    0.092        0.671   0.253
Matched-pair guard (seed 1), windowed               0.880               0.983     0.984               0.442      0.238    0.099        0.683   0.313
Matched-pair guard (seed 2), truncated              0.867               0.950     0.969               0.250      0.336    0.247        0.680   0.521
Matched-pair guard (seed 2), windowed               0.907               0.967     0.969               0.258      0.375    0.294        0.690   0.558
No-twin ablation, truncated                         0.873               0.933     0.849               0.396      0.250    0.151        0.705   0.473
No-twin ablation, windowed                          0.940               1.000     0.849               0.413      0.269    0.162        0.723   0.500
PIGuard                                             0.920               0.933     0.210               0.252      0.021    0.064        0.951   0.527
Paraphrase-augmented, truncated                     0.880               0.933     0.987               0.220      0.176    0.147        0.687   0.558
Paraphrase-augmented, windowed                      0.907               1.000     0.987               0.221      0.199    0.169        0.701   0.625
Prismor-1.5B                                        0.087               0.050     0.000               0.683      0.755    0.822        0.036   0.159
Prompt-Guard-2 22M                                  0.307               0.617     0.642               0.709      0.590    0.631        0.317   0.608
Prompt-Guard-2 86M                                  0.053               0.400     0.539               0.730      0.715    0.790        0.104   0.579
ProtectAI v1                                        0.007               0.000     0.287               0.057      0.021    0.067        0.004   0.233
ProtectAI v2                                        0.000               0.017     0.077               0.037      0.028    0.011        0.007   0.101
Sheltron 68M                                        0.873               0.950     0.273               0.213      0.188    0.238        0.572   0.952
Size-matched control, truncated                     0.807               0.917     0.917               0.198      0.086    0.072        0.651   0.104
Size-matched control, windowed                      0.820               0.950     0.917               0.201      0.086    0.072        0.656   0.108
TestSavant L                                        0.047               0.800     0.317               0.321      0.312    0.226        0.163   0.245
Wolf Defender                                       0.920               0.950     0.447               0.915      0.882    0.882        0.835   1.000
deepset DeBERTa                                     0.027               0.133     0.071               0.127      0.208    0.219        0.049   0.187
fmops DistilBERT                                    0.013               0.017     0.901               0.223      0.340    0.540        0.022   0.848
```
