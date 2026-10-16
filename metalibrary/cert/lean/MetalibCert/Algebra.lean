/-
The mod-3 lambda algebra (Ivanov–Mikhailov–Wu, arXiv:1506.00952, §2) as executable code.
A third implementation, next to `lambda3.py`/`rust/` and `cert/check.py`; it shares no code with them.

Generators λᵢ (i ≥ 1, degree 4i-1) and μⱼ (j ≥ 0, degree 4j). With
  a(k,j) = (-1)^{j+1} C(2(k-j)-1, j),  b(k,j) = (-1)^j C(2(k-j), j),
  N(k) = k - ⌈(k+1)/3⌉,  N'(k) = k - ⌈k/3⌉,
an inadmissible pair is rewritten by
  λᵢ λ_{3i+k} = Σ_{j≤N(k)} a(k,j) λ_{i+k-j} λ_{3i+j}
  λᵢ μ_{3i+k} = Σ_{j≤N(k)} a(k,j) λ_{i+k-j} μ_{3i+j} + Σ_{j≤N'(k)} b(k,j) μ_{i+k-j} λ_{3i+j}
  μᵢ λ_{3i+k+1} = Σ_{j≤N(k)} a(k,j) μ_{i+k-j} λ_{3i+j+1}
  μᵢ μ_{3i+k+1} = Σ_{j≤N(k)} a(k,j) μ_{i+k-j} μ_{3i+j+1}
and the differential is the derivation with
  ∂λₖ = Σ_{j=1}^{N(k)} a(k,j) λ_{k-j} λⱼ,
  ∂μₖ = Σ_{j=0}^{N(k)} a(k,j) λ_{k-j} μⱼ + Σ_{j=1}^{N'(k)} b(k,j) μ_{k-j} λⱼ.
Admissible: after λᵢ the next index is ≤ 3i-1, after μᵢ it is ≤ 3i. Normal forms: rewrite the
leftmost inadmissible pair. Coefficients are natural numbers mod 3.
-/
import Std.Data.HashMap
import Std.Data.HashSet

namespace MetalibCert

open Std

structure Letter where
  mu : Bool
  i : Nat
deriving BEq, Hashable, Repr, Inhabited

abbrev Word := List Letter
/-- A linear combination of words over 𝔽₃: coefficients in {1, 2}. -/
abbrev Comb := HashMap Word Nat

def deg (x : Letter) : Nat := 4 * x.i - (if x.mu then 0 else 1)

/-- C(n, k) mod 3 by Lucas' theorem. -/
partial def binom3 (n k : Nat) : Nat :=
  if n == 0 && k == 0 then 1
  else
    let a := n % 3
    let b := k % 3
    if b > a then 0
    else (if b == 0 || b == a then 1 else 2) * binom3 (n / 3) (k / 3) % 3

def neg3 (c : Nat) : Nat := (3 - c % 3) % 3

def coefA (k j : Nat) : Nat :=
  let c := binom3 (2 * (k - j) - 1) j
  if (j + 1) % 2 == 0 then c else neg3 c

def coefB (k j : Nat) : Nat :=
  let c := binom3 (2 * (k - j)) j
  if j % 2 == 0 then c else neg3 c

/-- `N k = k - ⌈(k+1)/3⌉` and `N' k = k - ⌈k/3⌉`; `N 0 = -1` (an empty sum). -/
def NN (k : Nat) : Int := (k : Int) - ((k + 3) / 3 : Nat)
def N1 (k : Nat) : Int := (k : Int) - ((k + 2) / 3 : Nat)

/-- `[0, 1, ..., m]` for `m : Int` (empty if `m < 0`). -/
def upTo (m : Int) : List Nat := List.range (m + 1).toNat
/-- `[1, ..., m]`. -/
def oneTo (m : Int) : List Nat := List.range' 1 m.toNat

def lam (i : Nat) : Letter := ⟨false, i⟩
def mu (i : Nat) : Letter := ⟨true, i⟩

def admissiblePair (x y : Letter) : Bool := decide (y.i ≤ 3 * x.i - (if x.mu then 0 else 1))

/-- `x y` for an inadmissible pair, as (coefficient, letter, letter), zero terms dropped. -/
def relation (x y : Letter) : List (Nat × Letter × Letter) :=
  let i := x.i
  let terms :=
    if !x.mu then
      let k := y.i - 3 * i
      if !y.mu then
        (upTo (NN k)).map fun j => (coefA k j, lam (i + k - j), lam (3 * i + j))
      else
        (upTo (NN k)).map (fun j => (coefA k j, lam (i + k - j), mu (3 * i + j))) ++
        (upTo (N1 k)).map (fun j => (coefB k j, mu (i + k - j), lam (3 * i + j)))
    else
      let k := y.i - 3 * i - 1
      (upTo (NN k)).map fun j => (coefA k j, mu (i + k - j), ⟨y.mu, 3 * i + j + 1⟩)
  terms.filter (·.1 % 3 != 0)

def dLetter (x : Letter) : List (Nat × Letter × Letter) :=
  let k := x.i
  let terms :=
    if !x.mu then
      (oneTo (NN k)).map fun j => (coefA k j, lam (k - j), lam j)
    else
      (upTo (NN k)).map (fun j => (coefA k j, lam (k - j), mu j)) ++
      (oneTo (N1 k)).map (fun j => (coefB k j, mu (k - j), lam j))
  terms.filter (·.1 % 3 != 0)

def addTo (acc : Comb) (w : Word) (c : Nat) : Comb :=
  let v := (acc.getD w 0 + c) % 3
  if v == 0 then acc.erase w else acc.insert w v

/-- The first position `p` with `(w[p], w[p+1])` inadmissible. -/
def firstBad : Word → Nat → Option Nat
  | x :: y :: rest, p => if admissiblePair x y then firstBad (y :: rest) (p + 1) else some p
  | _, _ => none

/-- Memo tables for normal forms and differentials. -/
structure Memo where
  nf : HashMap Word (List (Word × Nat)) := {}
  d : HashMap Word (List (Word × Nat)) := {}
  cells : HashMap (Nat × Nat × Nat) (List Word) := {}

abbrev M := StateM Memo

partial def normal (w : Word) : M (List (Word × Nat)) := do
  if let some r := (← get).nf.get? w then return r
  let r ← match firstBad w 0 with
    | none => pure [(w, 1)]
    | some p => do
      let x := w[p]!
      let y := w[p + 1]!
      let pre := w.take p
      let post := w.drop (p + 2)
      let mut acc : Comb := {}
      for (c, a, b) in relation x y do
        for (u, cu) in (← normal (pre ++ [a, b] ++ post)) do
          acc := addTo acc u (c * cu)
      pure acc.toList
  modify fun m => { m with nf := m.nf.insert w r }
  return r

/-- ∂w in normal form; λ has odd degree, so the sign changes after every λ. -/
def dWord (w : Word) : M (List (Word × Nat)) := do
  if let some r := (← get).d.get? w then return r
  let mut acc : Comb := {}
  let mut sign := 1
  let mut p := 0
  for x in w do
    for (c, a, b) in dLetter x do
      for (u, cu) in (← normal (w.take p ++ [a, b] ++ w.drop (p + 1))) do
        acc := addTo acc u (sign * c * cu)
    if !x.mu then sign := 3 - sign
    p := p + 1
  let r := acc.toList
  modify fun m => { m with d := m.d.insert w r }
  return r

/-- Words of a cell (n, s, c): admissible, first letter λ₁ or μ₁ (Λ(1)), last letter a λ,
degree n - 3, length s, c letters μ. (μ₀ can only be followed by μ₀, so it never occurs.) -/
partial def enumW (s c : Nat) (pre : List Letter) (len rem mus : Nat) : List Word :=
  if len == s then
    if rem == 0 && mus == c && (match pre with | x :: _ => !x.mu | [] => false) then [pre.reverse] else []
  else if rem < 3 * (s - len) || mus > c then []
  else
    let hi := match pre with
      | [] => 1
      | x :: _ => 3 * x.i - (if x.mu then 0 else 1)
    (List.range' 1 hi).flatMap fun i =>
      [false, true].flatMap fun m =>
        let x : Letter := ⟨m, i⟩
        if deg x ≤ rem then enumW s c (x :: pre) (len + 1) (rem - deg x) (mus + if m then 1 else 0)
        else []

def cellWords (n s c : Nat) : List Word :=
  if s == 0 || n < 3 then [] else enumW s c [] 0 (n - 3) 0

/-- `cellWords`, memoised. -/
def cell (n s c : Nat) : M (List Word) := do
  if let some r := (← get).cells.get? (n, s, c) then return r
  let r := cellWords n s c
  modify fun m => { m with cells := m.cells.insert (n, s, c) r }
  return r

end MetalibCert
