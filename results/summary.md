## Scorecard at 9 req/s (mean of seeds, +-95% CI half-width)

| Strategy | n | Chat on time | Batch on time | Goodput (req/s) | p99 chat TTFT (s) | Slowest batch (s) | Chat on time, steady-state middle 60% |
|---|---|---|---|---|---|---|---|
| FCFS | 5 | 1 +-1% | 67 +-7% | 3.3 +-0.4 | 151 | 196 | 0% |
| Class priority | 5 | 66 +-8% | 20 +-5% | 4.1 +-0.5 | 2 | 280 | 66% |
| Shortest-first | 5 | 44 +-2% | 78 +-2% | 5.9 +-0.2 | 390 | 454 | 44% |
| EDF | 5 | 50 +-11% | 20 +-5% | 3.4 +-0.7 | 61 | 260 | 58% |
| EDF + triage | 5 | 93 +-2% | 47 +-5% | 6.8 +-0.2 | 336 | 367 | 93% |
| SlackSched tiers | 5 | 91 +-2% | 37 +-4% | 6.2 +-0.2 | 343 | 379 | 91% |
| Least slack | 5 | 81 +-3% | 43 +-5% | 6.0 +-0.3 | 354 | 365 | 84% |
| Class + triage (ours) | 5 | 83 +-3% | 54 +-4% | 6.6 +-0.3 | 369 | 350 | 82% |
| Shortest-prompt-first (ours) | 5 | 63 +-2% | 87 +-1% | 7.2 +-0.2 | 372 | 457 | 62% |

## Chat on time (TTFT SLO) vs load

| Strategy | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|
| FCFS | 91% | 39% | 5% | 2% | 1% |
| Class priority | 96% | 89% | 82% | 75% | 66% |
| Shortest-first | 91% | 72% | 55% | 50% | 44% |
| EDF | 98% | 96% | 91% | 63% | 50% |
| EDF + triage | 98% | 97% | 95% | 94% | 93% |
| SlackSched tiers | 98% | 96% | 94% | 93% | 91% |
| Least slack | 98% | 96% | 94% | 88% | 81% |
| Class + triage (ours) | 96% | 93% | 89% | 86% | 83% |
| Shortest-prompt-first (ours) | 98% | 84% | 73% | 69% | 63% |

## Batch on time vs load

| Strategy | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|
| FCFS | 100% | 100% | 100% | 88% | 67% |
| Class priority | 100% | 100% | 84% | 35% | 20% |
| Shortest-first | 100% | 99% | 92% | 84% | 78% |
| EDF | 100% | 100% | 84% | 35% | 20% |
| EDF + triage | 100% | 100% | 92% | 62% | 47% |
| SlackSched tiers | 100% | 99% | 79% | 48% | 37% |
| Least slack | 100% | 100% | 93% | 57% | 43% |
| Class + triage (ours) | 100% | 100% | 98% | 70% | 54% |
| Shortest-prompt-first (ours) | 100% | 100% | 96% | 91% | 87% |

## Goodput (on-time requests / arrival span) vs load

| Strategy | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|
| FCFS | 5.13 | 4.47 | 3.98 | 3.87 | 3.33 |
| Class priority | 5.26 | 6.09 | 6.23 | 4.71 | 4.11 |
| Shortest-first | 5.12 | 5.52 | 5.55 | 5.74 | 5.89 |
| EDF | 5.32 | 6.30 | 6.57 | 4.23 | 3.37 |
| EDF + triage | 5.32 | 6.33 | 7.06 | 6.69 | 6.76 |
| SlackSched tiers | 5.33 | 6.29 | 6.52 | 6.03 | 6.18 |
| Least slack | 5.33 | 6.32 | 7.03 | 6.19 | 5.99 |
| Class + triage (ours) | 5.27 | 6.21 | 7.02 | 6.68 | 6.62 |
| Shortest-prompt-first (ours) | 5.31 | 5.94 | 6.33 | 6.88 | 7.24 |

## Non-stationarity check (FCFS & EDF+triage): chat on time in first 1000 vs last 1000 requests

| Strategy | load | first 1k | middle 60% | last 1k | makespan (s) |
|---|---|---|---|---|---|
| FCFS | 5 | 91% | 91% | 91% | 565 |
| FCFS | 6 | 52% | 38% | 22% | 481 |
| FCFS | 7 | 15% | 0% | 0% | 473 |
| FCFS | 8 | 5% | 0% | 0% | 473 |
| FCFS | 9 | 4% | 0% | 0% | 472 |
| EDF | 5 | 98% | 98% | 99% | 565 |
| EDF | 6 | 96% | 95% | 95% | 481 |
| EDF | 7 | 91% | 92% | 90% | 473 |
| EDF | 8 | 87% | 77% | 17% | 473 |
| EDF | 9 | 79% | 58% | 1% | 472 |
| EDF + triage | 5 | 98% | 98% | 99% | 565 |
| EDF + triage | 6 | 97% | 96% | 96% | 481 |
| EDF + triage | 7 | 96% | 95% | 95% | 473 |
| EDF + triage | 8 | 94% | 94% | 94% | 474 |
| EDF + triage | 9 | 93% | 93% | 94% | 474 |
| Least slack | 5 | 98% | 98% | 99% | 565 |
| Least slack | 6 | 96% | 96% | 96% | 481 |
| Least slack | 7 | 94% | 94% | 94% | 473 |
| Least slack | 8 | 92% | 91% | 77% | 473 |
| Least slack | 9 | 90% | 84% | 63% | 473 |

## Prediction-noise sweep (least slack; shortest-first), mean over seeds

| load | strategy/mode | metric | s=0 | 0.5 | 1 | 1.5 | 2 |
|---|---|---|---|---|---|---|---|
| 7 | llf/rank | chat_ontime | 94+-2 | 94+-2 | 94+-2 | 94+-2 | 94+-2 |
| 7 | llf/rank | batch_ontime | 92+-6 | 92+-6 | 92+-6 | 92+-6 | 92+-6 |
| 7 | llf/rank | max_batch_e2e | 165s | 165s | 165s | 165s | 165s |
| 7 | llf/point | chat_ontime | 94+-1 | 94+-1 | 95+-1 | 94+-1 | 94+-2 |
| 7 | llf/point | batch_ontime | 93+-6 | 93+-6 | 93+-5 | 93+-5 | 93+-4 |
| 7 | llf/point | max_batch_e2e | 153s | 157s | 184s | 405s | 433s |
| 7 | llf/upper | chat_ontime | 94+-1 | 94+-1 | 94+-1 | 95+-1 | 94+-2 |
| 7 | llf/upper | batch_ontime | 93+-6 | 94+-5 | 93+-4 | 90+-1 | 83+-2 |
| 7 | llf/upper | max_batch_e2e | 153s | 152s | 434s | 431s | 430s |
| 7 | sjf/point | chat_ontime | 55+-2 | 56+-2 | 56+-3 | 57+-3 | 57+-2 |
| 7 | sjf/point | batch_ontime | 92+-2 | 91+-2 | 91+-1 | 90+-1 | 90+-2 |
| 7 | sjf/point | max_batch_e2e | 431s | 435s | 436s | 436s | 436s |
| 9 | llf/rank | chat_ontime | 81+-3 | 81+-3 | 81+-3 | 81+-3 | 81+-3 |
| 9 | llf/rank | batch_ontime | 44+-3 | 44+-3 | 44+-3 | 44+-3 | 44+-3 |
| 9 | llf/rank | max_batch_e2e | 361s | 361s | 361s | 361s | 361s |
| 9 | llf/point | chat_ontime | 81+-3 | 81+-3 | 81+-2 | 81+-2 | 80+-3 |
| 9 | llf/point | batch_ontime | 43+-4 | 44+-3 | 45+-3 | 47+-3 | 49+-3 |
| 9 | llf/point | max_batch_e2e | 365s | 363s | 366s | 400s | 422s |
| 9 | llf/upper | chat_ontime | 81+-3 | 80+-2 | 80+-3 | 81+-3 | 85+-3 |
| 9 | llf/upper | batch_ontime | 43+-4 | 46+-3 | 55+-2 | 59+-3 | 56+-3 |
| 9 | llf/upper | max_batch_e2e | 365s | 356s | 412s | 412s | 422s |
| 9 | sjf/point | chat_ontime | 44+-1 | 45+-2 | 44+-2 | 44+-2 | 44+-2 |
| 9 | sjf/point | batch_ontime | 78+-2 | 77+-2 | 75+-2 | 74+-2 | 73+-2 |
| 9 | sjf/point | max_batch_e2e | 454s | 458s | 459s | 459s | 458s |

## Stress variants (mean over seeds)

| variant | load | strategy | n | chat on time | batch on time | goodput | p99 chat TTFT (s) | slowest batch (s) | preemption restarts |
|---|---|---|---|---|---|---|---|---|---|
| bursty | 7 | Class priority | 3 | 65% | 98% | 5.58 | 2 | 142 | 0 |
| bursty | 9 | Class priority | 3 | 45% | 24% | 3.06 | 3 | 255 | 0 |
| bursty | 7 | Class + triage (ours) | 3 | 77% | 100% | 6.07 | 277 | 108 | 0 |
| bursty | 9 | Class + triage (ours) | 3 | 70% | 82% | 6.72 | 393 | 242 | 0 |
| bursty | 7 | EDF | 3 | 78% | 98% | 6.04 | 2 | 141 | 0 |
| bursty | 9 | EDF | 3 | 36% | 24% | 2.64 | 45 | 235 | 0 |
| bursty | 7 | EDF + triage | 3 | 88% | 100% | 6.45 | 272 | 116 | 0 |
| bursty | 9 | EDF + triage | 3 | 86% | 65% | 6.67 | 389 | 308 | 0 |
| bursty | 7 | FCFS | 3 | 4% | 100% | 3.50 | 35 | 113 | 0 |
| bursty | 9 | FCFS | 3 | 1% | 80% | 3.52 | 122 | 170 | 0 |
| bursty | 7 | Least slack | 3 | 86% | 100% | 6.37 | 293 | 111 | 0 |
| bursty | 9 | Least slack | 3 | 77% | 62% | 6.14 | 391 | 298 | 0 |
| bursty | 7 | Shortest-first | 3 | 43% | 96% | 4.71 | 218 | 346 | 0 |
| bursty | 9 | Shortest-first | 3 | 34% | 81% | 5.06 | 391 | 458 | 0 |
| ddl300 | 7 | Class priority | 3 | 82% | 100% | 6.82 | 1 | 182 | 0 |
| ddl300 | 9 | Class priority | 3 | 65% | 100% | 7.94 | 2 | 282 | 0 |
| ddl300 | 7 | EDF | 3 | 92% | 100% | 7.18 | 2 | 182 | 0 |
| ddl300 | 9 | EDF | 3 | 78% | 100% | 8.56 | 2 | 282 | 0 |
| ddl300 | 7 | EDF + triage | 3 | 95% | 100% | 7.32 | 315 | 163 | 0 |
| ddl300 | 9 | EDF + triage | 3 | 93% | 100% | 9.30 | 390 | 259 | 0 |
| ddl300 | 7 | FCFS | 3 | 4% | 100% | 3.93 | 62 | 129 | 0 |
| ddl300 | 9 | FCFS | 3 | 1% | 100% | 4.91 | 149 | 197 | 0 |
| ddl300 | 7 | Least slack | 3 | 94% | 100% | 7.27 | 359 | 152 | 0 |
| ddl300 | 9 | Least slack | 3 | 90% | 100% | 9.16 | 414 | 253 | 0 |
| ddl300 | 7 | Shortest-first | 3 | 55% | 97% | 5.71 | 353 | 430 | 0 |
| ddl300 | 9 | Shortest-first | 3 | 44% | 92% | 6.58 | 389 | 451 | 0 |
| kv8k | 7 | Class priority | 3 | 73% | 81% | 5.78 | 2 | 171 | 3 |
| kv8k | 9 | Class priority | 3 | 56% | 18% | 3.52 | 3 | 270 | 3 |
| kv8k | 7 | Class + triage (ours) | 3 | 82% | 100% | 6.83 | 401 | 130 | 3 |
| kv8k | 9 | Class + triage (ours) | 3 | 76% | 60% | 6.55 | 374 | 356 | 6 |
| kv8k | 7 | EDF | 3 | 84% | 81% | 6.20 | 3 | 170 | 1 |
| kv8k | 9 | EDF | 3 | 42% | 18% | 2.85 | 65 | 249 | 4 |
| kv8k | 7 | EDF + triage | 3 | 94% | 96% | 7.10 | 324 | 147 | 3 |
| kv8k | 9 | EDF + triage | 3 | 91% | 51% | 6.84 | 344 | 363 | 5 |
| kv8k | 7 | FCFS | 3 | 4% | 100% | 3.91 | 65 | 119 | 1 |
| kv8k | 9 | FCFS | 3 | 1% | 67% | 3.32 | 152 | 191 | 4 |
| kv8k | 7 | Least slack | 3 | 92% | 97% | 7.09 | 377 | 138 | 3 |
| kv8k | 9 | Least slack | 3 | 80% | 48% | 6.15 | 367 | 357 | 3 |
| kv8k | 7 | Shortest-first | 3 | 50% | 91% | 5.32 | 360 | 434 | 34 |
| kv8k | 9 | Shortest-first | 3 | 42% | 77% | 5.76 | 400 | 461 | 104 |
| mix80 | 7 | Class priority | 3 | 34% | 27% | 2.44 | 5 | 315 | 0 |
| mix80 | 9 | Class priority | 3 | 2% | 2% | 0.23 | 57 | 408 | 0 |
| mix80 | 7 | Class + triage (ours) | 3 | 77% | 100% | 6.13 | 360 | 105 | 0 |
| mix80 | 9 | Class + triage (ours) | 3 | 66% | 52% | 6.12 | 332 | 391 | 0 |
| mix80 | 7 | EDF | 3 | 23% | 27% | 1.76 | 35 | 215 | 0 |
| mix80 | 9 | EDF | 3 | 4% | 2% | 0.35 | 113 | 288 | 0 |
| mix80 | 7 | EDF + triage | 3 | 89% | 92% | 6.72 | 374 | 163 | 0 |
| mix80 | 9 | EDF + triage | 3 | 82% | 42% | 7.10 | 322 | 401 | 0 |
| mix80 | 7 | FCFS | 3 | 4% | 100% | 1.78 | 62 | 125 | 0 |
| mix80 | 9 | FCFS | 3 | 1% | 65% | 1.38 | 149 | 191 | 0 |
| mix80 | 7 | Least slack | 3 | 85% | 93% | 6.51 | 380 | 159 | 0 |
| mix80 | 9 | Least slack | 3 | 68% | 43% | 6.09 | 327 | 383 | 0 |
| mix80 | 7 | Shortest-first | 3 | 55% | 91% | 4.67 | 357 | 429 | 0 |
| mix80 | 9 | Shortest-first | 3 | 44% | 76% | 4.86 | 388 | 449 | 0 |
| n10k | 6 | Class priority | 2 | 91% | 100% | 6.04 | 1 | 113 | 0 |
| n10k | 7 | Class priority | 2 | 83% | 25% | 3.98 | 1 | 424 | 0 |
| n10k | 9 | Class priority | 2 | 68% | 6% | 3.51 | 2 | 752 | 0 |
| n10k | 6 | Class + triage (ours) | 2 | 93% | 100% | 6.11 | 160 | 105 | 0 |
| n10k | 7 | Class + triage (ours) | 2 | 90% | 51% | 5.21 | 1229 | 1008 | 0 |
| n10k | 9 | Class + triage (ours) | 2 | 85% | 20% | 4.96 | 1056 | 1136 | 0 |
| n10k | 6 | EDF | 2 | 96% | 100% | 6.20 | 1 | 114 | 0 |
| n10k | 7 | EDF | 2 | 35% | 25% | 2.19 | 130 | 327 | 0 |
| n10k | 9 | EDF | 2 | 15% | 6% | 0.98 | 405 | 602 | 0 |
| n10k | 6 | EDF + triage | 2 | 97% | 100% | 6.24 | 104 | 109 | 0 |
| n10k | 7 | EDF + triage | 2 | 95% | 45% | 5.19 | 946 | 1024 | 0 |
| n10k | 9 | EDF + triage | 2 | 94% | 18% | 5.27 | 983 | 1091 | 0 |
| n10k | 6 | FCFS | 2 | 34% | 100% | 4.26 | 11 | 104 | 0 |
| n10k | 7 | FCFS | 2 | 2% | 51% | 1.96 | 194 | 262 | 0 |
| n10k | 9 | FCFS | 2 | 0% | 21% | 1.04 | 490 | 546 | 0 |
| n10k | 6 | Least slack | 2 | 97% | 100% | 6.23 | 131 | 99 | 0 |
| n10k | 7 | Least slack | 2 | 88% | 36% | 4.59 | 1064 | 1012 | 0 |
| n10k | 9 | Least slack | 2 | 68% | 15% | 3.94 | 1018 | 1088 | 0 |
| truepoisson | 7 | Class priority | 3 | 81% | 96% | 6.34 | 1 | 150 | 0 |
| truepoisson | 9 | Class priority | 3 | 66% | 23% | 4.08 | 2 | 267 | 0 |
| truepoisson | 7 | EDF | 3 | 93% | 96% | 6.73 | 2 | 150 | 0 |
| truepoisson | 9 | EDF | 3 | 52% | 23% | 3.41 | 51 | 249 | 0 |
| truepoisson | 7 | EDF + triage | 3 | 95% | 100% | 6.96 | 294 | 137 | 0 |
| truepoisson | 9 | EDF + triage | 3 | 93% | 52% | 6.63 | 345 | 349 | 0 |
| truepoisson | 7 | FCFS | 3 | 5% | 100% | 3.77 | 44 | 115 | 0 |
| truepoisson | 9 | FCFS | 3 | 2% | 73% | 3.46 | 134 | 185 | 0 |
| truepoisson | 7 | Least slack | 3 | 95% | 100% | 6.94 | 327 | 128 | 0 |
| truepoisson | 9 | Least slack | 3 | 82% | 47% | 5.93 | 367 | 349 | 0 |
| truepoisson | 7 | Shortest-first | 3 | 56% | 94% | 5.37 | 305 | 428 | 0 |
| truepoisson | 9 | Shortest-first | 3 | 46% | 79% | 5.74 | 386 | 448 | 0 |
