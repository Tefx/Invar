/**
 * Test max-function-lines in Core (limit: 65 lines)
 */

/**
 * Valid function - 64 lines (within limit)
 *
 * @example
 * validCoreFunction() // => 'done'
 */
export function validCoreFunction(): string {
  // Line 10
  const a = 1;
  const b = 2;
  const c = 3;
  const d = 4;
  const e = 5;
  const f = 6;
  const g = 7;
  const h = 8;
  const i = 9;
  const j = 10; // Line 20
  const k = 11;
  const l = 12;
  const m = 13;
  const n = 14;
  const o = 15;
  const p = 16;
  const q = 17;
  const r = 18;
  const s = 19;
  const t = 20; // Line 30
  const u = 21;
  const v = 22;
  const w = 23;
  const x = 24;
  const y = 25;
  const z = 26;
  const aa = 27;
  const bb = 28;
  const cc = 29;
  const dd = 30; // Line 40
  const ee = 31;
  const ff = 32;
  const gg = 33;
  const hh = 34;
  const ii = 35;
  const jj = 36;
  const kk = 37;
  const ll = 38;
  const mm = 39;
  const nn = 40; // Line 50
  const oo = 41;
  const pp = 42;
  const qq = 43;
  const rr = 44;
  const ss = 45;
  const tt = 46;
  const uu = 47;
  const vv = 48;
  const ww = 49;
  const xx = 50; // Line 60
  const yy = 51;
  const zz = 52;
  return 'done'; // Line 64
}

/**
 * Invalid function - 70 lines (exceeds Core limit of 65)
 *
 * @example
 * invalidCoreFunction() // => 'done'
 */
export function invalidCoreFunction(): string {
  // Line 74
  const a = 1;
  const b = 2;
  const c = 3;
  const d = 4;
  const e = 5;
  const f = 6;
  const g = 7;
  const h = 8;
  const i = 9;
  const j = 10;
  const k = 11;
  const l = 12;
  const m = 13;
  const n = 14;
  const o = 15;
  const p = 16;
  const q = 17;
  const r = 18;
  const s = 19;
  const t = 20;
  const u = 21;
  const v = 22;
  const w = 23;
  const x = 24;
  const y = 25;
  const z = 26;
  const aa = 27;
  const bb = 28;
  const cc = 29;
  const dd = 30;
  const ee = 31;
  const ff = 32;
  const gg = 33;
  const hh = 34;
  const ii = 35;
  const jj = 36;
  const kk = 37;
  const ll = 38;
  const mm = 39;
  const nn = 40;
  const oo = 41;
  const pp = 42;
  const qq = 43;
  const rr = 44;
  const ss = 45;
  const tt = 46;
  const uu = 47;
  const vv = 48;
  const ww = 49;
  const xx = 50;
  const yy = 51;
  const zz = 52;
  const aaa = 53;
  const bbb = 54;
  const ccc = 55;
  const ddd = 56;
  const eee = 57;
  const fff = 58;
  const ggg = 59;
  const hhh = 60;
  const iii = 61;
  const jjj = 62;
  const kkk = 63;
  const lll = 64;
  const mmm = 65;
  const nnn = 66;
  return 'done'; // Line 143 (70 lines from line 74)
}
