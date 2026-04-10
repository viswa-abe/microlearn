---
concept: indirection-the-power-of-one-more-layer
title: "Indirection: the power of one more layer"
topic: "Programming Concepts"
depth: 3
connections: [recursion-self-reference-that-bottoms-out, state-the-hidden-variable, abstraction-is-pattern-extraction]
source: {type: seed}
created: 2026-04-10
---

## Idea
"Any problem in CS can be solved by adding another level of indirection." Instead of pointing to the thing, **point to something that points to the thing**. This lets you change what the pointer targets without changing everything that uses it.

## Example
Your contact list has phone numbers. But people change numbers. DNS: you type `google.com`, not `142.250.80.46`. The name is indirection -- it can point to different servers without you knowing. Variables in code: the name `x` is indirection over a memory address.

## Probe
Every URL is indirection (name -> IP). Every variable name is indirection (name -> value). Every API is indirection (interface -> implementation). What's the cost of all this indirection? When does adding another layer make things worse?
