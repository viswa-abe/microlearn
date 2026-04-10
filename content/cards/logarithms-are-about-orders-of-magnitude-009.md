---
concept: logarithms-are-about-orders-of-magnitude
title: "Logarithms are about orders of magnitude"
topic: "Math Intuition"
depth: 1
connections: [exponential-growth-the-doubling-trick, patterns-are-compression]
source: {type: seed}
created: 2026-04-10
---

## Idea
A logarithm answers: **how many times do I multiply?** That's it. `log10(1000) = 3` because 10 x 10 x 10 = 1000. Logarithms turn multiplication into addition and turn exponential growth into straight lines. That's why they're everywhere.

## Example
```
1         -> log10 = 0
10        -> log10 = 1
100       -> log10 = 2
1,000     -> log10 = 3
1,000,000 -> log10 = 6
```
Each step is 10x bigger, but the log only goes up by 1. This is how your ears work -- a sound 10x more powerful sounds only "one step" louder. Decibels are logarithmic.

## Probe
The Richter scale is logarithmic. A magnitude 7 earthquake is *10 times* more powerful than a 6, and *100 times* more than a 5. Why would scientists choose a scale that hides how dramatic the differences really are?
