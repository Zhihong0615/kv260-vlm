# RM09 PL0 overlay probe result

The corrected probe entered with the starter-kit active at 99,999,999Hz. It
armed the 30-minute rollback timer, unloaded the starter-kit, and loaded the
separate RM07 overlay app successfully. FCLK0 still read 99,999,999Hz after the
app load, so the rate guard stopped the run before APM calibration, tensor
execution, or the 135-call replay. No above-100MHz work ran.

The trap unloaded the variant, reset FCLK0 to 100MHz, and restored the
starter-kit. Restore log reports PASS; the final FPGA manager state was
`operating`, FCLK0 was 99,999,999Hz, and frozen RM07 package hashes passed.

Pre-load diagnostics recorded `pl0_ref_mux=1,499,999,985Hz` and
`pl0_ref_div1=99,999,999Hz`. The live device-tree `fclk0` node is `xlnx,fclk`
with clock ID 71. The overlay's `assigned-clock-rates` did not alter the
observed FCLK0 rate. The captured `couldn't set sdio1_ref clk rate` kernel
messages refer to SDIO1 and are not evidence about FCLK0.

The next and only planned clock attempt is a guarded direct sysfs write of
187,498,123Hz, while no app is loaded. The script requires readback within
1MHz of target and at or below the 187,512,000Hz routed ceiling, then requires
post-load readback, APM, and real-tensor numeric gates before replay. It arms
the 30-minute restore timer before unloading and restores 100MHz starter-kit
on every exit. Staged script SHA-256:
`90d7a21421bf23f6b05c78ab9293b439957fa3f95cfb2ac0dac05946155717fe`.

The method follows the official [Xilinx `xilinx_fclk.c` sysfs implementation](https://github.com/Xilinx/linux-xlnx/blob/master/drivers/staging/fclk/xilinx_fclk.c), which rounds the request with `clk_round_rate()`, applies it through `clk_set_rate()`, and exposes the resulting `clk_get_rate()` readback.
