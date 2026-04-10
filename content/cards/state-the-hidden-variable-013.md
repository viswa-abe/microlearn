---
concept: state-the-hidden-variable
title: "State: the hidden variable"
topic: "Programming Concepts"
depth: 2
connections: [recursion-self-reference-that-bottoms-out, indirection-the-power-of-one-more-layer, feedback-loops-amplify-or-stabilize]
source: {type: seed}
created: 2026-04-10
---

## Idea
A function with no state always gives the same output for the same input. A function *with* state can give **different outputs depending on what happened before**. Most bugs come from unexpected state. Most complexity comes from managing it.

## Example
A light switch: same input (flip), different output (on -> off, off -> on). The switch has *state* -- it remembers whether it's on or off. A calculator with a memory button has state. A pure math function like sin(x) does not.

## Probe
A traffic light cycles green -> yellow -> red -> green. It's stateful -- the next color depends on the current one. But the *sequence* is fixed. Is a traffic light more or less complex than a light switch? What makes state hard to reason about?
