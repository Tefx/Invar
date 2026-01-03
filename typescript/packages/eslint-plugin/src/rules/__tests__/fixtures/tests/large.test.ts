/**
 * Valid Tests file - tests layer has highest limits
 * Tests: layer-detection (tests), max-file-lines (tests: 1300), max-function-lines (tests: 260)
 */

import { describe, it, expect } from 'vitest';

describe('Example test suite', () => {
  it('should pass', () => {
    expect(true).toBe(true);
  });

  /**
   * Large test function - valid for tests layer (260 line limit)
   * This would fail in Core (65) or Shell (130)
   */
  it('large test function - within 260 line limit', () => {
    const data: number[] = [];
    // Line 20
    data.push(1);
    data.push(2);
    data.push(3);
    data.push(4);
    data.push(5);
    data.push(6);
    data.push(7);
    data.push(8);
    data.push(9);
    data.push(10); // Line 30
    data.push(11);
    data.push(12);
    data.push(13);
    data.push(14);
    data.push(15);
    data.push(16);
    data.push(17);
    data.push(18);
    data.push(19);
    data.push(20); // Line 40
    data.push(21);
    data.push(22);
    data.push(23);
    data.push(24);
    data.push(25);
    data.push(26);
    data.push(27);
    data.push(28);
    data.push(29);
    data.push(30); // Line 50
    data.push(31);
    data.push(32);
    data.push(33);
    data.push(34);
    data.push(35);
    data.push(36);
    data.push(37);
    data.push(38);
    data.push(39);
    data.push(40); // Line 60
    data.push(41);
    data.push(42);
    data.push(43);
    data.push(44);
    data.push(45);
    data.push(46);
    data.push(47);
    data.push(48);
    data.push(49);
    data.push(50); // Line 70
    data.push(51);
    data.push(52);
    data.push(53);
    data.push(54);
    data.push(55);
    data.push(56);
    data.push(57);
    data.push(58);
    data.push(59);
    data.push(60); // Line 80
    data.push(61);
    data.push(62);
    data.push(63);
    data.push(64);
    data.push(65);
    data.push(66);
    data.push(67);
    data.push(68);
    data.push(69);
    data.push(70); // Line 90
    data.push(71);
    data.push(72);
    data.push(73);
    data.push(74);
    data.push(75);
    data.push(76);
    data.push(77);
    data.push(78);
    data.push(79);
    data.push(80); // Line 100
    data.push(81);
    data.push(82);
    data.push(83);
    data.push(84);
    data.push(85);
    data.push(86);
    data.push(87);
    data.push(88);
    data.push(89);
    data.push(90); // Line 110
    data.push(91);
    data.push(92);
    data.push(93);
    data.push(94);
    data.push(95);
    data.push(96);
    data.push(97);
    data.push(98);
    data.push(99);
    data.push(100); // Line 120
    data.push(101);
    data.push(102);
    data.push(103);
    data.push(104);
    data.push(105);
    data.push(106);
    data.push(107);
    data.push(108);
    data.push(109);
    data.push(110); // Line 130
    data.push(111);
    data.push(112);
    data.push(113);
    data.push(114);
    data.push(115);
    data.push(116);
    data.push(117);
    data.push(118);
    data.push(119);
    data.push(120); // Line 140
    data.push(121);
    data.push(122);
    data.push(123);
    data.push(124);
    data.push(125);
    data.push(126);
    data.push(127);
    data.push(128);
    data.push(129);
    data.push(130); // Line 150
    data.push(131);
    data.push(132);
    data.push(133);
    data.push(134);
    data.push(135);
    data.push(136);
    data.push(137);
    data.push(138);
    data.push(139);
    data.push(140); // Line 160
    data.push(141);
    data.push(142);
    data.push(143);
    data.push(144);
    data.push(145);
    data.push(146);
    data.push(147);
    data.push(148);
    data.push(149);
    data.push(150); // Line 170
    data.push(151);
    data.push(152);
    data.push(153);
    data.push(154);
    data.push(155);
    data.push(156);
    data.push(157);
    data.push(158);
    data.push(159);
    data.push(160); // Line 180
    data.push(161);
    data.push(162);
    data.push(163);
    data.push(164);
    data.push(165);
    data.push(166);
    data.push(167);
    data.push(168);
    data.push(169);
    data.push(170); // Line 190
    data.push(171);
    data.push(172);
    data.push(173);
    data.push(174);
    data.push(175);
    data.push(176);
    data.push(177);
    data.push(178);
    data.push(179);
    data.push(180); // Line 200
    data.push(181);
    data.push(182);
    data.push(183);
    data.push(184);
    data.push(185);
    data.push(186);
    data.push(187);
    data.push(188);
    data.push(189);
    data.push(190); // Line 210
    data.push(191);
    data.push(192);
    data.push(193);
    data.push(194);
    data.push(195);
    data.push(196);
    data.push(197);
    data.push(198);
    data.push(199);
    data.push(200); // Line 220
    data.push(201);
    data.push(202);
    data.push(203);
    data.push(204);
    data.push(205);
    data.push(206);
    data.push(207);
    data.push(208);
    data.push(209);
    data.push(210); // Line 230
    data.push(211);
    data.push(212);
    data.push(213);
    data.push(214);
    data.push(215);
    data.push(216);
    data.push(217);
    data.push(218);
    data.push(219);
    data.push(220); // Line 240
    data.push(221);
    data.push(222);
    data.push(223);
    data.push(224);
    data.push(225);
    data.push(226);
    data.push(227);
    data.push(228);
    data.push(229);
    data.push(230); // Line 250
    data.push(231);
    data.push(232);
    data.push(233);
    data.push(234);
    data.push(235);
    data.push(236);
    data.push(237);
    data.push(238);
    data.push(239);
    data.push(240); // Line 260
    expect(data.length).toBe(240);
  }); // Line 262 - within 260 limit
});
