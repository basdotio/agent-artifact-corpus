@ Library symbols agbcc emits by name, at their ROM addresses (Thumb).
	.syntax unified
	.global memcpy
	.thumb_set memcpy, 0x08056440
	.global __divsi3
	.thumb_set __divsi3, 0x080561A0
	.global __modsi3
	.thumb_set __modsi3, 0x08056238
	.global __udivsi3
	.thumb_set __udivsi3, 0x08056308
	.global __umodsi3
	.thumb_set __umodsi3, 0x08056380
	.global _call_via_r0
	.thumb_set _call_via_r0, 0x08056164
	.global _call_via_r1
	.thumb_set _call_via_r1, 0x08056168
	.global _call_via_r2
	.thumb_set _call_via_r2, 0x0805616C
	.global _call_via_r3
	.thumb_set _call_via_r3, 0x08056170
	.global _call_via_r4
	.thumb_set _call_via_r4, 0x08056174
	.global _call_via_r5
	.thumb_set _call_via_r5, 0x08056178
	.global _call_via_r6
	.thumb_set _call_via_r6, 0x0805617C
	.global _call_via_r7
	.thumb_set _call_via_r7, 0x08056180
	.global _call_via_r8
	.thumb_set _call_via_r8, 0x08056184
	.global _call_via_r9
	.thumb_set _call_via_r9, 0x08056188
	.global _call_via_sl
	.thumb_set _call_via_sl, 0x0805618C
	.global _call_via_fp
	.thumb_set _call_via_fp, 0x08056190
	.global _call_via_ip
	.thumb_set _call_via_ip, 0x08056194
	.global _call_via_lr
	.thumb_set _call_via_lr, 0x08056198
