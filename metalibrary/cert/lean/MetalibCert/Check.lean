/-
Checking the certificates in Lean, and the rapacious rule. Same checks as `cert/check.py`
(see its docstring), on this file's own lambda algebra (`Algebra.lean`).
-/
import MetalibCert.Algebra

namespace MetalibCert

open Std

abbrev Cell := Nat × Nat × Nat

def num (t : String) : Nat :=
  t.toList.foldl (fun a ch => a * 10 + (ch.toNat - '0'.toNat)) 0

def parseWord (t : String) : Word :=
  (t.splitOn ".").map fun x =>
    match x.toList with
    | ch :: rest => ⟨ch == 'm', rest.foldl (fun a d => a * 10 + (d.toNat - '0'.toNat)) 0⟩
    | [] => ⟨false, 0⟩

def tokens (txt : String) : List (List String) :=
  ((txt.splitOn "\n").map fun l => (l.splitOn " ").filter (· != "")).filter (· != [])

def parseTerm (t : String) : Option (Word × Nat) :=
  match t.splitOn ":" with
  | [w, k] => some (parseWord w, num k % 3)
  | _ => none

def index (ws : List Word) : HashMap Word Nat :=
  (ws.foldl (fun (m, i) w => (m.insert w i, i + 1)) (({} : HashMap Word Nat), 0)).1

/-- `Σ k · ∂w` over the terms, or `none` if a term is malformed, a word is not in `src`, or some
`∂w` leaves the target index. -/
def dComb (terms : List String) (src tgt : HashMap Word Nat) : M (Option Comb) := do
  let mut acc : Comb := {}
  for t in terms do
    match parseTerm t with
    | none => return none
    | some (w, k) =>
      if !src.contains w then return none
      for (u, cu) in (← dWord w) do
        if !tgt.contains u then return none
        acc := addTo acc u (k * cu)
  return some acc

/-- A block certificate: lines `y t w:k ...`; `∂y` contains its pivot `t` and no later pivot.
Returns the block and the certified lower bound for the rank. -/
def checkBlock (txt : String) : M (Option (Cell × Nat)) := do
  match tokens txt with
  | ["block", n, s, c, "words", w, "targets", t, "rank", r] :: rest =>
    let (n, s, c, r) := (num n, num s, num c, num r)
    let src ← cell n s c
    let tgt ← cell (n - 1) (s + 1) c
    if src.length != num w || tgt.length != num t then return none
    if rest.getLast? != some ["end"] then return none
    let ys := rest.filter (·.head? == some "y")
    if ys.length != r then return none
    let si := index src
    let ti := index tgt
    let pivs := ys.map fun y => parseWord (y.getD 1 "")
    let mut pos : HashMap Nat Nat := {}
    let mut i := 0
    for p in pivs do
      match ti.get? p with
      | none => return none
      | some j =>
        if pos.contains j then return none
        pos := pos.insert j i
      i := i + 1
    i := 0
    for y in ys do
      match ← dComb (y.drop 2) si ti with
      | none => return none
      | some acc =>
        if !acc.contains (pivs.getD i []) then return none
        for (u, _) in acc.toList do
          if (pos.getD (ti.getD u 0) 0) > i then return none
      i := i + 1
    return some ((n, s, c), r)
  | _ => return none

/-- Determinant over 𝔽₃ (Laplace expansion; the matrices here are tiny). -/
partial def det3 : List (List Nat) → Nat
  | [] => 1
  | r :: rs =>
    ((List.range r.length).foldl (fun a j =>
      let m := det3 (rs.map (·.eraseIdx j))
      let t := r.getD j 0 * m
      a + (if j % 2 == 0 then t else 2 * t)) 0) % 3

/-- A cell certificate: `dim` cycles z (∂z = 0) and cocycles φ (φ ∘ ∂ = 0 on the cell above)
with an invertible pairing; returns the cell and the lower bound `dim`. -/
def checkCell (txt : String) : M (Option (Cell × Nat)) := do
  match tokens txt with
  | ["cell", n, s, c, "words", w, "dim", h] :: rest =>
    let (n, s, c, h) := (num n, num s, num c, num h)
    let x ← cell n s c
    if x.length != num w || rest.getLast? != some ["end"] then return none
    let xi := index x
    let bi := index (← cell (n - 1) (s + 1) c)
    let zs := rest.filter (·.head? == some "z")
    let fs := rest.filter (·.head? == some "phi")
    if zs.length != h || fs.length != h then return none
    for z in zs do
      match ← dComb (z.drop 1) xi bi with
      | some acc => if acc.size != 0 then return none
      | none => return none
    let mut phis : List (HashMap Word Nat) := []
    for f in fs do
      let mut m : HashMap Word Nat := {}
      for t in f.drop 1 do
        match parseTerm t with
        | some (w, k) => if !xi.contains w then return none
                         m := m.insert w k
        | none => return none
      phis := phis ++ [m]
    let above ← if s ≥ 2 then cell (n + 1) (s - 1) c else pure []
    for u in above do
      let du ← dWord u
      for (v, _) in du do
        if !xi.contains v then return none
      for f in phis do
        if (du.foldl (fun a (v, k) => a + f.getD v 0 * k) 0) % 3 != 0 then return none
    let zmaps := zs.map fun z => (z.drop 1).filterMap parseTerm
    let pairing := zmaps.map fun z => phis.map fun f => (z.foldl (fun a (v, k) => a + f.getD v 0 * k) 0) % 3
    if det3 pairing == 0 then return none
    return some ((n, s, c), h)
  | _ => return none

/-- d² = 0 on every word of the cell. -/
def d2zero (n s c : Nat) : M Bool := do
  for w in ← cell n s c do
    let mut acc : Comb := {}
    for (u, k) in ← dWord w do
      for (v, kk) in ← dWord u do
        acc := addTo acc v (k * kk)
    if acc.size != 0 then return false
  return true

/-- The rapacious rule on the cells `E`: pages r = 2, 3, ...; arrows (n,s,c) → (n-1,s+r,c+1)
of maximal total rank; the arrows of a page form disjoint chains, filled from the high-n end
(`high = true`) or the low-n end. Returns the survivors in the columns `cols`. -/
def rule (E0 : List (Cell × Nat)) (high : Bool) (cols : List Nat) : List Nat := Id.run do
  let mut E : HashMap Cell Nat := E0.foldl (fun m (k, v) => m.insert k v) {}
  let rmax := E0.foldl (fun a ((_, s, _), _) => max a s) 0 + 1
  for r in List.range' 2 rmax do
    let tgt := fun (v : Cell) => ((v.1 - 1, v.2.1 + r, v.2.2 + 1) : Cell)
    let live := E.toList.filter fun (v, k) => k > 0 && E.getD (tgt v) 0 > 0
    let nxt : HashMap Cell Cell := live.foldl (fun m (v, _) => m.insert v (tgt v)) {}
    let hit : HashSet Cell := live.foldl (fun m (v, _) => m.insert (tgt v)) {}
    let mut flows : List (Cell × Cell × Nat) := []
    for (v, _) in live do
      if hit.contains v then continue
      let mut chain : Array Cell := #[v]
      let mut cur := v
      for _ in List.range (rmax * 1000) do
        match nxt.get? cur with
        | some u => chain := chain.push u; cur := u
        | none => break
      let mut used : HashMap Cell Nat := {}
      let steps := List.range (chain.size - 1)
      for i in (if high then steps else steps.reverse) do
        let a := chain[i]!
        let b := chain[i + 1]!
        let f := min (E.getD a 0 - used.getD a 0) (E.getD b 0 - used.getD b 0)
        if f > 0 then
          used := (used.insert a (used.getD a 0 + f)).insert b (used.getD b 0 + f)
          flows := (a, b, f) :: flows
    for (a, b, f) in flows do
      E := (E.insert a (E.getD a 0 - f)).insert b (E.getD b 0 - f)
  return cols.map fun N => E.toList.foldl (fun a ((n, _, _), k) => if n == N then a + k else a) 0

/-- Keeps the memo tables bounded (memory on the worker is capped); only speed depends on them. -/
def trim : M Unit :=
  modify fun m => { m with
    nf := if m.nf.size > 2000000 then {} else m.nf
    d := if m.d.size > 300000 then {} else m.d }

/-- Everything `cert/check.py` checks. On success: for every column N, (N, survivors with the
high fill, survivors with the low fill). -/
def checkAll (cellsTxt : String) (blocks cells : List String) (cols : List Nat) :
    Option (List (Nat × Nat × Nat)) := (go).run' {}
where
  go : M (Option (List (Nat × Nat × Nat))) := do
    let claimL : List (Cell × Nat) := (tokens cellsTxt).filterMap fun
      | [n, s, c, d] => if n.startsWith "#" then none else some ((num n, num s, num c), num d)
      | _ => none
    let claim : HashMap Cell Nat := claimL.foldl (fun m (k, v) => m.insert k v) {}
    -- the conventions: d² = 0 on the small claimed cells
    for ((n, s, c), _) in claimL do
      if (← cell n s c).length ≤ 300 then
        if !(← d2zero n s c) then return none
    let mut rk : HashMap Cell Nat := {}
    for b in blocks do
      match ← checkBlock b with
      | some (k, r) => rk := rk.insert k r
      | none => return none
      trim
    let mut low : HashMap Cell Nat := {}
    for t in cells do
      match ← checkCell t with
      | some (k, h) => low := low.insert k h
      | none => return none
    -- exact dimensions
    for ((n, s, c), dim) in claimL do
      let w := (← cell n s c).length
      let out := if (← cell (n - 1) (s + 1) c).isEmpty then 0 else rk.getD (n, s, c) 0
      let inn := if s ≥ 2 then rk.getD (n + 1, s - 1, c) 0 else 0
      if w != dim + out + inn then return none
      if dim != 0 && low.get? (n, s, c) != some dim then return none
    -- closure
    let smax := claimL.foldl (fun a ((_, s, _), _) => max a s) 0 + 30
    for ((n, s, c), dim) in claimL do
      if dim == 0 then continue
      for r in List.range' 2 (smax - 2) do
        if !(← cell (n - 1) (s + r) (c + 1)).isEmpty && !claim.contains (n - 1, s + r, c + 1) then
          return none
        if s > r && c ≥ 1 then
          if !(← cell (n + 1) (s - r) (c - 1)).isEmpty && !claim.contains (n + 1, s - r, c - 1) then
            return none
    for N in cols do
      for s in List.range' 1 N do
        for c in List.range s do
          if !(← cell N s c).isEmpty && !claim.contains (N, s, c) then return none
    let E := claimL.filter (·.2 > 0)
    let hi := rule E true cols
    let lo := rule E false cols
    return some (cols.zip (hi.zip lo))

end MetalibCert
