---
concept: recursion-self-reference-that-bottoms-out
title: "Recursion: self-reference that bottoms out"
topic: "Programming Concepts"
depth: 1
connections: [state-the-hidden-variable, indirection-the-power-of-one-more-layer, abstraction-is-pattern-extraction]
source: {type: seed}
created: 2026-04-10
---

## Idea
Recursion is when something is **defined in terms of a smaller version of itself**, plus a base case that stops it. Without the base case, you get infinite regress. With it, you get an elegant way to solve problems that have nested structure.

## Example
```
How to count people in a line:
1. If no one is in front of you: say "1"
2. Otherwise: ask the person ahead
   to count, then add 1
```
Each person solves a smaller problem (shorter line) until someone hits the base case (no one ahead). The answer builds up as the calls return.

## Probe
Russian nesting dolls are recursive -- each contains a smaller version of itself. File system folders are recursive -- each can contain more folders. What makes some problems *naturally* recursive vs. just loopy?
