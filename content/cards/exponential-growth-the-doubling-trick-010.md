---
concept: exponential-growth-the-doubling-trick
title: "Exponential growth: the doubling trick"
topic: "Math Intuition"
depth: 2
connections: [logarithms-are-about-orders-of-magnitude, probability-updating-beliefs]
source: {type: seed}
created: 2026-04-10
---

## Idea
Anything growing by a **fixed percentage** is growing exponentially. The key intuition: use the **Rule of 72**. Divide 72 by the growth rate to get the doubling time. 6% growth? Doubles in 12 years. 1% growth? 72 years.

## Example
If a city grows at 3% per year, it doubles in 72 / 3 = 24 years. Sounds slow -- but doubling means the city needs to build as much infrastructure in the *next* 24 years as it built in its *entire history*. That's why exponential growth is hard to manage.

## Probe
Bacteria double every 20 minutes. Start with one. After 10 hours (30 doublings): 2^30 ~ 1 billion. After 10.5 hours (just 3 more doublings): 8 billion. Why does the last half-hour matter more than the first 9 hours?
