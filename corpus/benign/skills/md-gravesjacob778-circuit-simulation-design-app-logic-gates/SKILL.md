---
name: logic-gates
description: Expert knowledge for digital logic gates including AND, OR, NOT, NAND, NOR, XOR, and XNOR gates. Use when designing digital circuits, implementing Boolean logic, creating truth tables, working with logic gate symbols, analyzing gate combinations, converting between gate types, or building digital systems. Covers basic and universal logic gates with truth tables, Boolean expressions, and circuit equivalents.
license: Complete terms in LICENSE.txt
---

# Logic Gates Expert

Comprehensive guide for working with digital logic gates in circuit design and digital electronics.

## When to Use This Skill

- Implementing logic gates in circuit simulation or design applications
- Creating or validating truth tables for logic operations
- Converting between different gate types (e.g., using NAND as universal gate)
- Designing Boolean logic circuits
- Understanding gate behavior and logical operations
- Building combinational or sequential digital circuits
- Teaching or explaining digital logic concepts
- Implementing gate-level circuit representations
- Analyzing or debugging digital logic designs

## Prerequisites

- Basic understanding of binary logic (0 and 1, LOW and HIGH)
- Familiarity with Boolean algebra concepts
- Understanding of digital circuits (for implementation)

## Basic Logic Gates

### AND Gate

The AND gate produces a HIGH output (1) **only when ALL inputs are HIGH**. If any input is LOW (0), the output is LOW.

**Boolean Expression**: `Y = A • B` or `Y = A AND B` or `Y = AB`

**2-Input Truth Table**:
```
A | B | Y
--|---|---
0 | 0 | 0
0 | 1 | 0
1 | 0 | 0
1 | 1 | 1
```

**Symbol**: AND gate symbol has a flat input side and curved output side.

**3-Input Variant**: `Y = A • B • C` (output HIGH only when A, B, and C are all HIGH)

### OR Gate

The OR gate produces a HIGH output (1) **when ANY input is HIGH**. Output is LOW only when all inputs are LOW.

**Boolean Expression**: `Y = A + B` or `Y = A OR B`

**2-Input Truth Table**:
```
A | B | Y
--|---|---
0 | 0 | 0
0 | 1 | 1
1 | 0 | 1
1 | 1 | 1
```

**Symbol**: OR gate symbol has a curved input side and pointed output side.

**3-Input Variant**: `Y = A + B + C` (output HIGH when any of A, B, or C is HIGH)

### NOT Gate (Inverter)

The NOT gate produces the **complement** of the input. It inverts the signal.

**Boolean Expression**: `Y = Ā` or `Y = NOT A` or `Y = A'`

**Truth Table**:
```
A | Y
--|---
0 | 1
1 | 0
```

**Symbol**: Triangle with a small circle (bubble) at the output.

**Note**: The NOT gate has only ONE input and ONE output.

## Universal Logic Gates

### NAND Gate

The NAND gate is the **combination of AND gate followed by NOT gate**. It is a universal gate - any Boolean function can be implemented using only NAND gates.

**Boolean Expression**: `Y = (A • B)'` or `Y = NAND(A, B)` (read as "A NAND B" or "NOT AND")

**Equivalent Circuit**: AND gate → NOT gate

**2-Input Truth Table**:
```
A | B | Y
--|---|---
0 | 0 | 1
0 | 1 | 1
1 | 0 | 1
1 | 1 | 0
```

**Symbol**: AND gate symbol with a bubble at the output.

**Key Property**: Output is LOW (0) **only when all inputs are HIGH**. Otherwise, output is HIGH (1).

### NOR Gate

The NOR gate is the **combination of OR gate followed by NOT gate**. It is also a universal gate - any Boolean function can be implemented using only NOR gates.

**Boolean Expression**: `Y = (A + B)'` or `Y = NOR(A, B)` (read as "A NOR B" or "NOT OR")

**Equivalent Circuit**: OR gate → NOT gate

**2-Input Truth Table**:
```
A | B | Y
--|---|---
0 | 0 | 1
0 | 1 | 0
1 | 0 | 0
1 | 1 | 0
```

**Symbol**: OR gate symbol with a bubble at the output.

**Key Property**: Output is HIGH (1) **only when all inputs are LOW**. Otherwise, output is LOW (0).

## Exclusive Gates

### XOR Gate (Exclusive OR)

The XOR gate produces a HIGH output **only when inputs are DIFFERENT**.

**Boolean Expression**: `Y = A ⊕ B` or `Y = A'B + AB'`

**2-Input Truth Table**:
```
A | B | Y
--|---|---
0 | 0 | 0
0 | 1 | 1
1 | 0 | 1
1 | 1 | 0
```

**Symbol**: OR gate symbol with an additional curved line at the input.

**Key Property**: Output is 1 when inputs differ, 0 when inputs are the same.

**Applications**: 
- Arithmetic circuits (addition, subtraction)
- Parity checkers
- Code converters
- Comparators

### XNOR Gate (Exclusive NOR)

The XNOR gate is the **combination of XOR gate followed by NOT gate**. Produces HIGH output **only when inputs are THE SAME**.

**Boolean Expression**: `Y = (A ⊕ B)'` or `Y = AB + A'B'`

**Equivalent Circuit**: XOR gate → NOT gate

**2-Input Truth Table**:
```
A | B | Y
--|---|---
0 | 0 | 1
0 | 1 | 0
1 | 0 | 0
1 | 1 | 1
```

**Symbol**: XOR gate symbol with a bubble at the output.

**Key Property**: Output is 1 when inputs are the same, 0 when inputs differ. Also called "equality detector" or "coincidence gate".

**Applications**:
- Arithmetic circuits
- Code converters
- Equality comparators

## Implementation Guidelines

### Gate Type Selection

| Requirement | Recommended Gate(s) |
|-------------|-------------------|
| All conditions must be true | AND |
| At least one condition must be true | OR |
| Invert signal | NOT |
| Minimal gate count design | NAND or NOR (universal) |
| Detect difference | XOR |
| Detect equality | XNOR |
| Need inverted AND logic | NAND |
| Need inverted OR logic | NOR |

### Multi-Input Gates

- **AND/OR/NAND/NOR**: Can be extended to 3+ inputs naturally
- **XOR/XNOR**: More than 2 inputs require cascading 2-input gates
  - 3-input XOR: Chain two 2-input XOR gates
  - Not typically available as discrete multi-input components

### Circuit Design Best Practices

1. **Start with truth table**: Define required behavior before selecting gates
2. **Use Boolean algebra**: Simplify expressions before implementing
3. **Minimize gate count**: Use universal gates (NAND/NOR) when appropriate
4. **Consider propagation delay**: Each gate adds delay to signal path
5. **Power consumption**: Fewer gates = lower power
6. **Check fan-out**: Ensure output can drive required number of inputs

### Common Logic Functions

#### 2-to-1 Multiplexer using gates:
```
Y = S'A + SB
(Where S is select, A and B are inputs)
```

#### Half Adder using XOR and AND:
```
Sum = A ⊕ B
Carry = A • B
```

#### Implementing AND with NAND only:
```
Y = (A NAND B) NAND (A NAND B)
```

#### Implementing OR with NAND only:
```
Y = (A NAND A) NAND (B NAND B)
```

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Output always HIGH | Input stuck at incorrect level for that gate type | Check input connections and logic levels |
| Output always LOW | Input stuck at incorrect level for that gate type | Verify input signals and gate type |
| Unexpected output | Wrong gate type selected | Review truth table and select correct gate |
| Circuit doesn't match spec | Boolean expression incorrect | Re-derive from truth table |
| XOR with 3+ inputs not working | Improper cascading | Use proper 2-input XOR chain structure |
| Universal gate conversion wrong | Incorrect transformation | Review conversion rules for NAND/NOR |

## Logic Gate Categories

### By Function
- **Basic Gates**: AND, OR, NOT (can build any logic circuit)
- **Universal Gates**: NAND, NOR (either one alone can build any circuit)
- **Exclusive Gates**: XOR, XNOR (for comparison operations)

### By Characteristics
- **Inverting**: NOT, NAND, NOR, XNOR
- **Non-inverting**: AND, OR, XOR
- **Single-input**: NOT
- **Multi-input**: AND, OR, NAND, NOR
- **Typically 2-input only**: XOR, XNOR

## Quick Reference

### Gate Symbols Summary
```
AND:   ──D───  (D shape, flat input side)
OR:    ──)───  (shield shape, curved input side)
NOT:   ──▷o──  (triangle with bubble)
NAND:  ──Do──  (AND with output bubble)
NOR:   ──)o──  (OR with output bubble)
XOR:   ──))──  (OR with extra input curve)
XNOR:  ──))o── (XOR with output bubble)
```

### Boolean Operator Precedence
1. NOT (highest)
2. AND
3. OR (lowest)

Use parentheses to override default precedence.

## Related Concepts

- **Boolean Algebra**: Mathematical framework for logic operations
- **Karnaugh Maps**: Visual method for simplifying Boolean expressions
- **DeMorgan's Theorems**: Rules for converting between AND/OR with negation
- **Combinational Circuits**: Circuits built from logic gates without memory
- **Sequential Circuits**: Circuits with feedback and memory elements
- **Truth Tables**: Complete specification of gate behavior
- **Timing Diagrams**: Visual representation of gate output over time

## References

- Digital logic design fundamentals
- Boolean algebra theorems
- Gate-level circuit optimization
- Universal gate conversions
- Logic family specifications (TTL, CMOS)

---

*This skill provides the foundational knowledge for digital logic design using logic gates. For more advanced topics like sequential circuits, state machines, or specific IC implementations, additional specialized skills may be needed.*
